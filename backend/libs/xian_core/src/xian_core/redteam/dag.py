"""战役计划执行运行时：调度 / 收益收敛 / 预算熔断（PRD 3.3.5.6）。

设计要点（技术方案 D5）：
- 静态分发由 Celery chain/group 承载；动态收敛由本运行时驱动；
- 收益递减（连续 2 轮无新发现）自动收敛；
- 单类别连续 5 次无成功自动更换变异算子或降权；
- 预算消耗 > 80% 且无新发现进入收尾挖掘阶段；
- 预算耗尽触发熔断（tripped），强制收尾出部分报告。
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from ..bus import bus, make_event
from ..schemas.campaign import DagNode
from ..schemas.common import CampaignStatus, Verdict
from .mutator import op_names, safe_op_names

CONVERGE_AFTER_IDLE_ROUNDS = 2
CATEGORY_FAIL_STREAK_LIMIT = 5
BUDGET_WARNING_RATIO = 0.8


@dataclass(slots=True)
class BudgetLedger:
    token_limit: int
    case_limit: int
    minute_limit: int
    tokens_used: int = 0
    cases_done: int = 0
    started_at: float = field(default_factory=time.monotonic)

    @property
    def minutes_used(self) -> float:
        return (time.monotonic() - self.started_at) / 60.0

    @property
    def budget_left(self) -> int:
        return max(0, self.token_limit - self.tokens_used)

    def consume(self, tokens: int) -> None:
        self.tokens_used += max(0, tokens)
        self.cases_done += 1

    @property
    def exhausted(self) -> bool:
        return (
            self.tokens_used >= self.token_limit
            or self.cases_done >= self.case_limit
            or self.minutes_used >= self.minute_limit
        )

    @property
    def nearly_exhausted(self) -> bool:
        return self.token_limit > 0 and self.tokens_used >= self.token_limit * BUDGET_WARNING_RATIO


@dataclass(slots=True)
class NodeState:
    node: DagNode
    success_count: int = 0
    attempt_count: int = 0
    fail_streak: int = 0
    current_ops: list[str] = field(default_factory=list)
    done: bool = False

    @property
    def asr(self) -> float:
        return self.success_count / self.attempt_count if self.attempt_count else 0.0


class CampaignRuntime:
    """按 DAG 调度攻击节点，带收益收敛与预算熔断。"""

    def __init__(
        self,
        campaign_id: Any,
        plan: dict[str, Any],
        budget: dict[str, Any],
        *,
        constraints: dict[str, Any] | None = None,
        publish: bool = True,
    ) -> None:
        self.campaign_id = str(campaign_id)
        self.nodes: dict[str, NodeState] = {}
        for raw in plan.get("dag_nodes", []):
            node = DagNode.model_validate(raw)
            self.nodes[node.id] = NodeState(node=node)
        self.ledger = BudgetLedger(
            token_limit=int(budget.get("token", 0) or 0),
            case_limit=int(budget.get("cases", 0) or 0),
            minute_limit=float(budget.get("minutes", 0) or 0),
        )
        self.constraints = constraints or {}
        self.publish = publish
        self.idle_rounds = 0
        self.new_findings = 0
        self.tripped = False
        self.history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ 调度
    def ready_nodes(self) -> list[NodeState]:
        """依赖满足且未完成的节点（无依赖用例可并发执行）。"""
        ready = []
        for state in self.nodes.values():
            if state.done:
                continue
            deps = state.node.depends_on
            if all(self.nodes[d].done for d in deps if d in self.nodes):
                ready.append(state)
        return ready

    def record(self, state: NodeState, verdict: Verdict, tokens: int) -> None:
        state.attempt_count += 1
        self.ledger.consume(tokens)
        if verdict in (Verdict.success, Verdict.partial):
            state.success_count += 1
            state.fail_streak = 0
            self.new_findings += 1
            self.idle_rounds = 0
        else:
            state.fail_streak += 1
            if state.fail_streak >= CATEGORY_FAIL_STREAK_LIMIT:
                state.current_ops = self._rotate_ops(state)
                state.fail_streak = 0
                state.node.weight = max(0.05, state.node.weight * 0.5)
        self.history.append(
            {
                "node": state.node.id,
                "verdict": verdict.value,
                "tokens": tokens,
                "asr_live": self.live_asr,
                "budget_left": self.ledger.budget_left,
            }
        )

    def _rotate_ops(self, state: NodeState) -> list[str]:
        """单类别连续 5 次无成功：更换变异算子（PRD 3.3.5.6）。"""
        pool = safe_op_names() if self.constraints.get("ops_per_case", 2) <= 2 else op_names()
        current = set(state.current_ops)
        for name in pool:
            if name not in current:
                return [name]
        return [pool[0]] if pool else []

    # ------------------------------------------------------------------ 收敛
    def should_converge(self) -> bool:
        if self.ledger.exhausted:
            self.tripped = True
            return True
        if self.ledger.nearly_exhausted and self.idle_rounds >= 1:
            self.tripped = True
            return True
        if self.idle_rounds >= CONVERGE_AFTER_IDLE_ROUNDS:
            return True
        return all(state.done for state in self.nodes.values())

    def mark_round_idle(self) -> None:
        self.idle_rounds += 1

    def mark_node_done(self, node_id: str) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].done = True

    @property
    def live_asr(self) -> float:
        total = sum(s.attempt_count for s in self.nodes.values())
        success = sum(s.success_count for s in self.nodes.values())
        return round(success / total, 4) if total else 0.0

    @property
    def status(self) -> CampaignStatus:
        return CampaignStatus.tripped if self.tripped else CampaignStatus.attacking

    def progress(self) -> int:
        total = len(self.nodes)
        if not total:
            return 0
        done = sum(1 for s in self.nodes.values() if s.done)
        return round(done / total * 100)

    # ------------------------------------------------------------------ 事件
    async def emit(self, event_type: str, message: str, payload: dict[str, Any] | None = None,
                   role: str = "commander") -> None:
        if not self.publish:
            return
        from ..schemas.events import Channel

        await bus.publish(
            Channel.campaign,
            self.campaign_id,
            make_event(event_type, role=role, message=message, payload=payload or {},
                       campaign_id=self.campaign_id),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "status": self.status.value,
            "progress": self.progress(),
            "asr_live": self.live_asr,
            "tokens_used": self.ledger.tokens_used,
            "budget_left": self.ledger.budget_left,
            "cases_done": self.ledger.cases_done,
            "minutes_used": round(self.ledger.minutes_used, 2),
            "new_findings": self.new_findings,
            "per_category": {nid: {"asr": s.asr, "attempts": s.attempt_count} for nid, s in self.nodes.items()},
            "tripped": self.tripped,
        }


def plan_nodes(plan: dict[str, Any]) -> list[DagNode]:
    return [DagNode.model_validate(raw) for raw in plan.get("dag_nodes", [])]


def topological_order(plan: dict[str, Any]) -> list[str]:
    """Kahn 拓扑排序：依赖优先，同层按权重降序。"""
    nodes = {n.id: n for n in plan_nodes(plan)}
    indegree = dict.fromkeys(nodes, 0)
    for node in nodes.values():
        for dep in node.depends_on:
            if dep in nodes:
                indegree[node.id] += 1
    ready = sorted([nid for nid, d in indegree.items() if d == 0],
                   key=lambda n: -nodes[n].weight)
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for node in nodes.values():
            if current in node.depends_on:
                indegree[node.id] -= 1
                if indegree[node.id] == 0:
                    ready.append(node.id)
        ready.sort(key=lambda n: -nodes[n].weight)
    order.extend([nid for nid in nodes if nid not in order])
    return order


def iterate_rounds(nodes: Iterable[NodeState]) -> list[NodeState]:
    return [s for s in nodes if not s.done]