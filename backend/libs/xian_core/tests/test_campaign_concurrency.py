"""战役执行器的 DAG 分层并发契约。

背景：PRD 3.3.5.8.1 规则③ 与详情页 PlanPreview 都声称"无箭头的节点并发执行"，
但 runner.execute_campaign 一度是逐条串行：图上画着并发，实际一条条排队打。
这里锁死四件事——层序尊重依赖、同层真的并发、落库按计划顺序串行、预算熔断不被打漏。
"""

from __future__ import annotations

import asyncio
import uuid

from xian_core.bus import bus
from xian_core.cases import cases_by_category  # noqa: F401  # 让用例库随导入就位
from xian_core.db.models import Campaign
from xian_core.redteam.commander import build_plan
from xian_core.redteam.runner import _case_layers, _concurrency_of, execute_campaign
from xian_core.schemas.campaign import Budget
from xian_core.schemas.common import Intensity
from xian_core.schemas.events import Channel

ALL_CATEGORIES = ["XM-01", "XM-02", "XM-03", "XM-04", "XM-05", "XM-06", "XM-07", "XM-08", "XM-09", "XM-10", "XM-11", "XM-12", "XM-13", "XM-14"]


class _RecordingClient:
    """记录并发度的假目标：每次 chat 睡一小会儿，用来观测层内是否真的并行。"""

    def __init__(self, delay: float = 0.02, tokens: int = 10) -> None:
        self.delay = delay
        self.tokens = tokens
        self.active = 0
        self.max_active = 0
        self.calls = 0

    async def chat(self, message: str, *, session_id: str | None = None) -> dict:
        self.active += 1
        self.calls += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(self.delay)
            return {"output": "ok", "events": [], "tokens": self.tokens, "session_id": session_id or ""}
        finally:
            self.active -= 1


def _plan(cases: int) -> dict:
    return build_plan(
        scope=ALL_CATEGORIES,
        intensity=Intensity.standard,
        budget=Budget(token=200000, cases=cases, minutes=30),
    )


def _campaign(plan: dict, *, cases: int, concurrency: int | None = None, token: int = 200000) -> Campaign:
    constraints = {"max_turns": 1}
    if concurrency is not None:
        constraints["concurrency"] = concurrency
    return Campaign(
        tenant_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        scope=ALL_CATEGORIES,
        intensity="standard",
        budget={"cases": cases, "token": token},
        constraints=constraints,
        status="attacking",
        judge_mode="standard",
        output_mode="summary",
        preset_id="standard",
        plan_dag=plan,
    )


def test_layers_follow_dag_dependencies() -> None:
    """依赖节点的用例必须排在依赖它的用例所在层之后。"""
    plan = _plan(40)
    layers = _case_layers(_campaign(plan, cases=40), 40)
    flat = [case.case_id for layer in layers for case in layer]
    assert len(flat) == 40
    assert len(set(flat)) == 40

    layer_of = {case.case_id: index for index, layer in enumerate(layers) for case in layer}
    cases_of = {node["id"]: node["case_ids"] for node in plan["dag_nodes"]}
    for node in plan["dag_nodes"]:
        for dep in node.get("depends_on") or []:
            for case_id in node["case_ids"]:
                for dep_case in cases_of.get(dep, []):
                    assert layer_of[dep_case] < layer_of[case_id], f"{dep} 的用例没有排在 {node[id]} 之前"


def test_layers_are_empty_without_usable_plan() -> None:
    """计划缺失或全是旧 ID 时返回空，让调用方回退 select_cases。"""
    base = {
        "tenant_id": uuid.uuid4(),
        "agent_id": uuid.uuid4(),
        "scope": ALL_CATEGORIES,
        "intensity": "standard",
        "budget": {},
        "constraints": {},
        "status": "attacking",
        "judge_mode": "standard",
        "output_mode": "summary",
        "preset_id": "standard",
    }
    assert _case_layers(Campaign(**base), 10) == []
    stale = Campaign(**{**base, "plan_dag": {"dag_nodes": [{"id": "XM-01", "case_ids": ["XM-99-001"]}]}})
    assert _case_layers(stale, 10) == []


def test_layers_respect_limit() -> None:
    """limit 必须照旧截断：执行条数不能超过预算。"""
    plan = _plan(40)
    assert sum(len(layer) for layer in _case_layers(_campaign(plan, cases=40), 7)) == 7


def test_concurrency_is_clamped() -> None:
    """并发度默认 4，可由 constraints 覆盖，但必须夹在 1~16。"""
    plan = _plan(40)
    assert _concurrency_of(_campaign(plan, cases=40)) == 4
    assert _concurrency_of(_campaign(plan, cases=40, concurrency=1)) == 1
    assert _concurrency_of(_campaign(plan, cases=40, concurrency=99)) == 16
    assert _concurrency_of(_campaign(plan, cases=40, concurrency=0)) == 1
    assert _concurrency_of(_campaign(plan, cases=40, concurrency="abc")) == 4


async def test_same_layer_runs_concurrently(session, tenant_id) -> None:
    """同层用例必须真的并发：观测到的最大并发数应等于配置的并发度。"""
    plan = _plan(40)
    campaign = _campaign(plan, cases=40, concurrency=4)
    session.add(campaign)
    await session.flush()

    client = _RecordingClient()
    result = await execute_campaign(campaign, session=session, tenant_id=tenant_id, client=client)

    assert result.executed == 40
    assert client.calls == 40
    assert client.max_active > 1, "同层用例仍是逐条串行，并发没有生效"
    assert client.max_active <= 4, f"并发度超过配置上限：{client.max_active}"


async def test_records_follow_plan_order(session, tenant_id) -> None:
    """落库必须串行且按计划顺序：records 顺序要和 DAG 清单逐条一致。"""
    plan = _plan(40)
    campaign = _campaign(plan, cases=40)
    session.add(campaign)
    await session.flush()

    result = await execute_campaign(campaign, session=session, tenant_id=tenant_id, client=_RecordingClient(0))

    expected = [case_id for node in plan["dag_nodes"] for case_id in node["case_ids"]]
    assert [r["case_id"] for r in result.records] == expected


async def test_budget_breaker_cuts_within_a_layer(session, tenant_id) -> None:
    """token 记账跟着投放走：预算必须能在层内刹住，不能整层一起放完。"""
    plan = _plan(40)
    campaign = _campaign(plan, cases=40, token=25)
    session.add(campaign)
    await session.flush()

    result = await execute_campaign(campaign, session=session, tenant_id=tenant_id,
                                    client=_RecordingClient(0, tokens=10))

    assert campaign.partial is True
    assert campaign.progress == 100
    assert result.executed <= 4, f"层内熔断失效，跑了 {result.executed} 条"
    assert result.tokens <= 40, f"层内熔断失效，烧了 {result.tokens} token"


async def test_budget_alert_is_emitted_once(session, tenant_id) -> None:
    """并发下熔断警报只能出现一次，不能每个跳过的用例都刷一条。"""
    plan = _plan(40)
    campaign = _campaign(plan, cases=40, token=25)
    session.add(campaign)
    await session.flush()

    await execute_campaign(campaign, session=session, tenant_id=tenant_id, client=_RecordingClient(0, tokens=10))

    alerts = [
        event
        for event in bus.history(Channel.campaign, campaign.id)
        if event.get("type") == "alert" and "预算" in str(event.get("message", ""))
    ]
    assert len(alerts) == 1, f"熔断警报重复上报 {len(alerts)} 次"
