"""战役执行器：API 内联执行与 Celery worker 共用同一套落库逻辑（PRD 3.3.5 / 3.3.6）。

设计要点：
- 入口 ``execute_campaign`` 只依赖 session 与 client 协议，不感知 Celery / FastAPI；
- 每条用例产出：ClickHouse trace 明细 + PG ``attack_records`` 结论摘要 + ``verdicts`` 判定流水；
- 预算与并发由调用方控制，执行器内部逐条推进并回写 campaign 进度，便于断点续跑。
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..bus import bus, make_event
from ..cases import get_case, select_cases
from ..db.repositories import AgentRepository
from ..db.models import AttackRecord, Campaign, Verdict
from ..llm.gateway import gateway as default_gateway
from ..schemas.common import Verdict as VerdictEnum
from ..schemas.common import enum_str
from ..schemas.events import Channel
from ..scoring.secscore import grade_of
from ..storage import ClickHouseStore
from .attacker import AttackOutcome, Attacker
from .clients import GatewayChatClient, SandboxChatClient, resolve_agent_client
from .payload import DEFAULT_VARIABLES


@dataclass(slots=True)
class CampaignExecution:
    """一次战役的执行结果摘要。"""

    campaign_id: str
    executed: int = 0
    success: int = 0
    partial: int = 0
    fail: int = 0
    unavailable: int = 0
    tokens: int = 0
    cost: float = 0.0
    sec_score: int | None = None
    grade: str = ""
    records: list[dict[str, Any]] = field(default_factory=list)

    @property
    def scored(self) -> int:
        """可判定样本数：目标不可达的样本不计入 ASR 分母（否则会把故障稀释成"守住了"）。"""
        return max(0, self.executed - self.unavailable)

    @property
    def asr(self) -> float:
        if not self.scored:
            return 0.0
        return round(self.success / self.scored, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "executed": self.executed,
            "success": self.success,
            "partial": self.partial,
            "fail": self.fail,
            "unavailable": self.unavailable,
            "tokens": self.tokens,
            "cost": round(self.cost, 6),
            "asr": self.asr,
            "sec_score": self.sec_score,
            "grade": self.grade,
            "records": self.records,
        }


def resolve_client(campaign: Campaign, *, runtime: Any | None = None, canary_values: list[str] | None = None):
    """按接入方式选择客户端：场景实例走沙箱，HTTP/SDK 接入走目标端点直连，其余走 LLM 网关。"""
    if campaign.scenario_instance_id is not None and runtime is not None:
        return SandboxChatClient(runtime, str(campaign.scenario_instance_id))
    return GatewayChatClient(default_gateway)


def resolve_campaign_client(campaign: Campaign, agent: Any | None = None, runtime: Any | None = None):
    """战役目标客户端：场景实例走沙箱，HTTP/SDK 接入直连目标端点，其余回退 LLM 网关。

    与模式二自由攻击（sessions.executor）走同一条解析规则，否则战役会永远落在离线回显上：
    跑得飞快，却拿不到任何真实观测。
    """
    from ..sandbox import client_for as sandbox_client_for

    if campaign.scenario_instance_id is not None:
        client = sandbox_client_for(campaign.scenario_instance_id)
        if client is not None:
            return client
        if runtime is not None:
            return SandboxChatClient(runtime, str(campaign.scenario_instance_id))
    if agent is not None:
        return resolve_agent_client(agent)
    return GatewayChatClient(default_gateway)


def _planned_cases(campaign: Campaign) -> list[Any]:
    """按落库的 DAG 计划取用例，按节点顺序（权重降序）返回。

    计划缺失、或里面的用例 ID 已下线/删除时返回空列表，
    由调用方回退到 select_cases。
    """
    dag = dict(campaign.plan_dag or {})
    nodes = dag.get("dag_nodes") or []
    if not isinstance(nodes, list):
        return []
    out: list[Any] = []
    seen: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        for case_id in node.get("case_ids") or []:
            key = str(case_id or '')
            if not key or key in seen:
                continue
            case = get_case(key)
            if case is None or case.status != "published":
                continue
            seen.add(key)
            out.append(case)
    return out


DEFAULT_CONCURRENCY = 4
MAX_CONCURRENCY = 16


def _case_layers(campaign: Campaign, limit: int = 0) -> list[list[Any]]:
    """把 DAG 计划用例按依赖深度切成可并发推进的层。

    commander 落库的 ``dag_nodes`` 已按拓扑序排列，这里再按 ``depends_on`` 还原依赖层：
    同一层内的用例彼此无依赖，可并发投放（PRD 3.3.5.8.1 规则③）；
    跨层仍按层序推进，提权/渗出类因此拿得到前序已泄露的上下文。
    计划不可用（缺失或全是旧 ID）时返回空列表，由调用方回退 select_cases。
    """
    dag = dict(campaign.plan_dag or {})
    nodes = [node for node in (dag.get("dag_nodes") or []) if isinstance(node, dict)]
    if not nodes:
        return []
    cases = _planned_cases(campaign)
    if limit:
        cases = cases[:limit]
    if not cases:
        return []
    depth: dict[str, int] = {}
    for node in nodes:  # dag_nodes 已是拓扑序，依赖必定排在自己前面
        deps = [str(dep) for dep in (node.get("depends_on") or [])]
        depth[str(node.get("id"))] = max((depth[d] for d in deps if d in depth), default=-1) + 1
    owner: dict[str, str] = {}
    for node in nodes:
        for case_id in node.get("case_ids") or []:
            owner[str(case_id)] = str(node.get("id"))
    order = {case.case_id: index for index, case in enumerate(cases)}
    layers: dict[int, list[Any]] = {}
    for case in cases:
        layers.setdefault(depth.get(owner.get(case.case_id, ""), 0), []).append(case)
    # 层内仍按计划顺序（拓扑序 + 同层权重降序）推进，报告清单才能和详情页 DAG 逐条对上
    return [sorted(layers[key], key=lambda case: order[case.case_id]) for key in sorted(layers)]


def _concurrency_of(campaign: Campaign) -> int:
    """层内并发度：默认 4，可由战役 constraints.concurrency 覆盖，夹在 1~16。"""
    raw = (campaign.constraints or {}).get("concurrency", DEFAULT_CONCURRENCY)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_CONCURRENCY
    return max(1, min(MAX_CONCURRENCY, value))


async def execute_campaign(
    campaign: Campaign,
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client: Any | None = None,
    runtime: Any | None = None,
    judge_mode: str = "",
    limit: int = 0,
    canary_values: list[str] | None = None,
    store: ClickHouseStore | None = None,
) -> CampaignExecution:
    """执行战役：按 DAG 依赖分层并发投放 -> 逐条判定 -> 串行落 trace 与 attack_record。"""
    attacker = Attacker()
    trace_store = store or ClickHouseStore()
    budget = dict(campaign.budget or {})
    max_cases = int(limit or budget.get("cases", 30) or 30)
    max_tokens = int(budget.get("token", 200000) or 200000)

    # 指挥官按攻击面优先级与历史战绩把预算切到每个类别（PRD 3.3.5.8.1 规则①②），
    # 执行器必须照单执行。之前这里另跑一套 select_cases，
    # 该算的权重再准也一条都不会影响实际打到哪里，详情页那份“可核对的执行清单”只是装饰。
    layers = _case_layers(campaign, max_cases)
    if not layers:
        fallback = select_cases(categories=list(campaign.scope) or None, limit=max_cases)
        if not fallback:
            fallback = select_cases(limit=max_cases)
        # 回退路径没有 DAG 依赖信息，只能逐条串行，保持旧行为
        layers = [[case] for case in fallback]
    cases = [case for layer in layers for case in layer]

    result = CampaignExecution(campaign_id=str(campaign.id))
    values = list(canary_values or (campaign.constraints or {}).get("canary_values", []) or [])
    # 用例模板里的 {{question}} / {{order_id}} 等占位符要先填好再下发：
    # 不然目标收到的是空壳，战役跑得快却没有任何真实观测，全场“未命中”。
    render_vars = {**DEFAULT_VARIABLES, **dict((campaign.constraints or {}).get("variables", {}) or {})}

    # 目标客户端在轮次外解析一次：HTTP/SDK 接入直连端点，不再一律回退离线回放
    agent = await AgentRepository(session, tenant_id).get_optional(campaign.agent_id)
    client = client if client is not None else resolve_campaign_client(campaign, agent, runtime=runtime)

    await _emit(campaign, "log", f"指挥官下单：{len(cases)} 条用例，预算 {max_tokens} token",
                {"cases": len(cases), "budget": max_tokens}, "commander")

    # 规则③：无依赖的用例并发投放。层由 plan_dag 的 depends_on 推出，
    # 同层用例彼此无依赖才并行，跨层仍等前序上下文就位。
    gate = asyncio.Semaphore(_concurrency_of(campaign))
    budget_alerted = False

    async def _budget_exhausted() -> bool:
        """token 预算熔断：命中即置 partial，并只上报一次，避免并发下重复刷警报。"""
        nonlocal budget_alerted
        if result.tokens < max_tokens:
            return False
        campaign.partial = True
        if not budget_alerted:
            budget_alerted = True
            await _emit(campaign, "alert", f"token 预算 {max_tokens} 已耗尽，战役提前收尾", {}, "system")
        return True

    async def _attack(case: Any) -> AttackOutcome | None:
        """单条用例的投放与判定：只做网络/LLM 交互，不碰数据库，可安全并发。"""
        if await _budget_exhausted():
            return None
        strategy_id = str((case.success_criteria or {}).get("strategy", ""))
        await _emit(campaign, "log", f"载荷下发：{case.case_id} {case.category_code}",
                    {"case_id": case.case_id, "category_code": case.category_code,
                     "strategy": strategy_id, "payload": case.payload_template}, "attacker")
        try:
            outcome = await attacker.execute(
                client,
                case_id=case.case_id,
                category_code=case.category_code,
                payload=case.payload_template,
                variables=render_vars,
                strategy_id=strategy_id,
                criteria=str(case.success_criteria.get("judge_hint", "")),
                judge_hint=case.judge_prompt,
                canary_values=values,
                signals=list((case.success_criteria or {}).get("golden", []) or []),
                max_turns=int((campaign.constraints or {}).get("max_turns", 3) or 3),
                session_id=str(campaign.id),
                subject_id=campaign.agent_id,
            )
        except Exception as exc:  # 目标不可达不应中断整场战役
            await _emit(campaign, "alert", f"{case.case_id} 目标调用失败：{exc}",
                        {"case_id": case.case_id, "category_code": case.category_code}, "system")
            return _unavailable_outcome(case.case_id, case.category_code, strategy_id, str(exc))
        # token 记账跟着投放走，不等落库：同层后续用例开场前就能看到已烧掉的额度，
        # 预算熔断才不会因为"整层一起放"而整层超支。
        result.tokens += int(outcome.tokens)
        result.cost += round(int(outcome.tokens) * 0.000002, 6)
        # 判定也在这里播报：_emit 只走总线不碰库，可安全并发，
        # 活动流于是随打随出，而不是等整层落库后一次性刷一批。
        await _emit(
            campaign,
            "verdict",
            f"{case.case_id} 判定 {enum_str(outcome.verdict)}：{outcome.reason or '-'}",
            {
                "case_id": outcome.case_id,
                "category_code": outcome.category_code,
                "verdict": enum_str(outcome.verdict),
                "confidence": outcome.confidence,
                "turns": outcome.turn_count,
                "tokens": outcome.tokens,
            },
            "judge",
        )
        return outcome

    async def _guarded(case: Any) -> AttackOutcome | None:
        async with gate:
            return await _attack(case)

    async def _persist(case: Any, outcome: AttackOutcome) -> None:
        """单条用例落库：PG 摘要 + verdicts 判定流水 + ClickHouse trace 明细。

        必须串行调用：AsyncSession 不是并发安全的；records 也要按计划顺序追加，
        报告里的执行清单才能和详情页 DAG 逐条对上。事件播报不在这里做。
        """
        record = AttackRecord(
            tenant_id=tenant_id,
            agent_id=campaign.agent_id,
            agent_version_id=campaign.agent_version_id,
            campaign_id=campaign.id,
            case_id=outcome.case_id,
            category_code=outcome.category_code,
            strategy=outcome.strategy_id,
            mutation_ops=list(outcome.escalated),
            turns=outcome.turn_count,
            verdict=enum_str(outcome.verdict),
            confidence=float(outcome.confidence),
            rule_hits=list(outcome.rule_hits),
            evidence=list(outcome.evidence),
            tokens=int(outcome.tokens),
            cost=round(int(outcome.tokens) * 0.000002, 6),
            trace_key=f"ch://trace_events/{tenant_id}/{campaign.id}",
        )
        session.add(record)
        await session.flush()

        trace_events: list[Any] = []
        for turn in outcome.turns:
            trace_events.extend(turn.events)
            trace_events.extend(
                _turn_events(
                    tenant_id=tenant_id,
                    subject_id=campaign.agent_id,
                    session_id=campaign.id,
                    turn=turn.turn,
                    prompt=turn.prompt,
                    output=turn.output,
                    tokens=turn.tokens,
                )
            )
        if not trace_events:
            # 目标不可用：也留一条可回放的事件，排障时能看到失败原因而不是空 trace
            trace_events = _unavailable_events(
                tenant_id=tenant_id,
                subject_id=campaign.agent_id,
                session_id=campaign.id,
                case_id=case.case_id,
                reason=outcome.reason,
            )
        for event in trace_events:
            await trace_store.insert_trace(event, tenant_id, record_id=str(record.id))

        session.add(
            Verdict(
                record_id=record.id,
                level="llm",
                result=enum_str(outcome.verdict),
                confidence=float(outcome.confidence),
                rule_hits=list(outcome.rule_hits),
                evidence=list(outcome.evidence),
                judge_model=outcome.judge_model or "xian-judge",
                reason=outcome.reason,
            )
        )

        result.executed += 1
        if enum_str(outcome.verdict) == str(VerdictEnum.success):
            result.success += 1
        elif enum_str(outcome.verdict) == str(VerdictEnum.partial):
            result.partial += 1
        elif enum_str(outcome.verdict) == str(VerdictEnum.unavailable):
            result.unavailable += 1
        else:
            result.fail += 1
        result.records.append(
            {
                "record_id": str(record.id),
                "case_id": outcome.case_id,
                "category_code": outcome.category_code,
                "verdict": enum_str(outcome.verdict),
                "confidence": outcome.confidence,
                "tokens": outcome.tokens,
                "turns": outcome.turn_count,
                "rule_hits": list(outcome.rule_hits),
            }
        )
        campaign.progress = min(100, int(result.executed * 100 / max(1, len(cases))))
        await session.flush()

    for layer in layers:
        if not layer:
            continue
        if await _budget_exhausted():
            break
        # gather 只负责"打"：并发跑完再统一串行落库，避免 AsyncSession 被并发写坏
        outcomes = await asyncio.gather(*(_guarded(case) for case in layer), return_exceptions=False)
        skipped = False
        for case, outcome in zip(layer, outcomes, strict=True):
            if outcome is None:
                skipped = True
                continue
            await _persist(case, outcome)
        if skipped:
            await _budget_exhausted()
            break

    result.sec_score = _sec_score(result)
    result.grade = grade_of(result.sec_score) if result.sec_score is not None else ""
    campaign.sec_score = result.sec_score
    campaign.grade = result.grade or None
    campaign.progress = 100
    campaign.ended_at = datetime.now(UTC)
    await _emit(campaign, "done", f"战役执行完成：命中 {result.success}、部分 {result.partial}、失败 {result.fail}、不可用 {result.unavailable}",
                {"executed": result.executed, "success": result.success, "partial": result.partial,
                 "fail": result.fail, "unavailable": result.unavailable, "sec_score": result.sec_score, "grade": result.grade}, "system")
    return result


async def _emit(campaign: Campaign, event_type: str, message: str, payload: dict[str, Any], role: str) -> None:
    """向 campaign:{id} 频道广播执行事件，详情页角色活动流经 WS 实时消费。"""
    try:
        await bus.publish(
            Channel.campaign,
            campaign.id,
            make_event(event_type, role=role, message=message, payload=payload, campaign_id=str(campaign.id)),
        )
    except Exception:  # pragma: no cover - 总线不可用不影响战役本身
        pass


def _unavailable_events(
    *, tenant_id: uuid.UUID, subject_id: uuid.UUID, session_id: uuid.UUID, case_id: str, reason: str
) -> list[Any]:
    """目标不可用时的兜底 trace：记录失败原因，保证记录可回放（PRD 3.4.4.8.2）。"""
    from ..schemas.attack import TraceEventIn

    return [
        TraceEventIn(
            subject_id=subject_id,
            session_id=session_id,
            event_type="output",
            actor="system",
            name=f"unavailable:{case_id}",
            args={"case_id": case_id},
            result={"error": reason[:400]},
        )
    ]


def _sec_score(result: CampaignExecution) -> int | None:
    """未失守即得分：1 - ASR，分母只统计可判定样本。

    一个可判定样本都没有时返回 None：此时给 0 分会被读成"安全性最差"，
    而事实是这场演练根本没测到东西（目标不可达），分数必须是"未评分"。
    """
    if not result.scored:
        return None
    return round((1 - result.asr) * 100)


def _unavailable_outcome(case_id: str, category_code: str, strategy_id: str, error: str) -> AttackOutcome:
    """目标不可用时给出 unavailable 结论，保证该用例仍留下记录可追溯。"""
    return AttackOutcome(
        case_id=case_id,
        category_code=category_code,
        strategy_id=strategy_id,
        verdict=VerdictEnum.unavailable,
        reason=f"目标不可用：{error[:120]}",
    )


def _turn_events(
    *,
    tenant_id: uuid.UUID,
    subject_id: uuid.UUID,
    session_id: uuid.UUID,
    turn: int,
    prompt: str,
    output: str,
    tokens: int = 0,
) -> list[Any]:
    """把每一轮问答折叠成一对输入/输出 trace 事件，保证 ClickHouse 明细可回放。"""
    from ..schemas.attack import TraceEventIn

    return [
        TraceEventIn(
            subject_id=subject_id,
            session_id=session_id,
            event_type="llm_call",
            actor="red",
            name=f"turn-{turn}-prompt",
            args={"prompt": prompt, "turn": turn},
            result={},
            tokens=tokens,
        ),
        TraceEventIn(
            subject_id=subject_id,
            session_id=session_id,
            event_type="output",
            actor="aut",
            name=f"turn-{turn}-output",
            args={},
            result={"output": output},
            tokens=tokens,
        ),
    ]
