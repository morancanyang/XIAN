"""战役计划 DAG 与执行器必须同源：DAG 是用例清单，不是装饰卡片。

背景：commander.build_plan 把预算按权重切到每个类别，并在节点上带出 case_ids；
但 runner.execute_campaign 之前完全忽略 plan_dag，另跑一套 select_cases。
结果详情页显示的“可核对执行清单”与实际打的用例无任何关系，
攻击面优先级与历史战术加权等于白算。
"""

from __future__ import annotations

import uuid

from xian_core.cases import all_cases, cases_by_category
from xian_core.db.models import Campaign
from xian_core.redteam.commander import build_plan
from xian_core.redteam.runner import _planned_cases
from xian_core.schemas.campaign import Budget
from xian_core.schemas.common import Intensity

ALL_CATEGORIES = ["XM-01", "XM-02", "XM-03", "XM-04", "XM-05", "XM-06", "XM-07", "XM-08", "XM-09", "XM-10", "XM-11", "XM-12", "XM-13", "XM-14"]


def _topological_violations(nodes: list[dict]) -> list[tuple[str, str]]:
    """返回“依赖出现在自己之后”的节点对；空列表表示顺序合法。"""
    position = {node["id"]: index for index, node in enumerate(nodes)}
    return [
        (node["id"], dep)
        for node in nodes
        for dep in node.get("depends_on") or []
        if dep in position and position[dep] > position[node["id"]]
    ]

def _plan(cases: int) -> dict:
    return build_plan(
        scope=ALL_CATEGORIES,
        intensity=Intensity.standard,
        budget=Budget(token=200000, cases=cases, minutes=30),
    )


def test_dag_case_total_equals_budget() -> None:
    """DAG 用例总数必须恰好等于预算（受库容量限制）。

    旧实现用 max(1, int(预算 * 份额)) 取整，既会丢份额又会溢出；
    实测 40 条预算只排出 34 条，执行器却另跑了 40 条。
    """
    available = sum(len(cases_by_category(code)) for code in ALL_CATEGORIES)
    for cases in (1, 3, 5, 14, 20, 40, 60, 134, 200, 500):
        plan = _plan(cases)
        nodes = plan["dag_nodes"]
        total = sum(node["budget_split"]["cases"] for node in nodes)
        listed = sum(len(node["case_ids"]) for node in nodes)
        assert total == listed, f"budget={cases} 分配与清单不一致"
        assert total == min(cases, available), f"budget={cases} 总数为 {total}"


def test_dag_case_ids_are_executable() -> None:
    """清单里的用例必须真存在且已发布，不能出现已下线 ID。"""
    published = {case.case_id for case in all_cases() if case.status == "published"}
    for node in _plan(40)["dag_nodes"]:
        assert node["case_ids"], f"{node[id]} 没有带出用例"
        for case_id in node["case_ids"]:
            assert case_id in published, f"{case_id} 不是可执行用例"


def test_budget_smaller_than_category_count_trims_nodes() -> None:
    """预算比类别数小时只保留权重最高的若干类，不能把预算腕超。"""
    for cases in (1, 3, 7):
        nodes = _plan(cases)["dag_nodes"]
        assert len(nodes) == cases, f"budget={cases} 却排了 {len(nodes)} 个节点"
        assert _topological_violations(nodes) == []


def test_planned_cases_mirror_the_dag() -> None:
    """执行器取用例必须照 DAG 清单，按节点顺序。"""
    plan = _plan(40)
    campaign = Campaign(
        tenant_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        scope=ALL_CATEGORIES,
        intensity="standard",
        budget={},
        constraints={},
        status="attacking",
        judge_mode="standard",
        output_mode="summary",
        preset_id="standard",
        plan_dag=plan,
    )
    picked = _planned_cases(campaign)
    expected = [case_id for node in plan["dag_nodes"] for case_id in node["case_ids"]]
    assert [case.case_id for case in picked] == expected
    assert len(picked) == 40


def test_planned_cases_falls_back_when_plan_is_unusable() -> None:
    """计划缺失或全是旧 ID 时返回空，让调用方回退 select_cases。"""
    base = dict(
        tenant_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        scope=ALL_CATEGORIES,
        intensity="standard",
        budget={},
        constraints={},
        status="attacking",
        judge_mode="standard",
        output_mode="summary",
        preset_id="standard",
    )
    assert _planned_cases(Campaign(**base)) == []
    stale = Campaign(**{**base, "plan_dag": {"dag_nodes": [{"id": "XM-01", "case_ids": ["XM-99-001"]}]}})
    assert _planned_cases(stale) == []


def test_plan_order_respects_dependencies() -> None:
    """规则③：提权/渗出类必须排在依赖的侦察/初始执行类之后。

    节点列表既是详情页 DAG 的渲染顺序，也是执行器取用例的顺序。
    之前按权重降序平铺，依赖只画在图上，提权用例会在侦察结果之前就跑完。
    """
    for cases in (14, 20, 40, 60):
        nodes = _plan(cases)["dag_nodes"]
        assert _topological_violations(nodes) == [], f"budget={cases} 存在逆依赖执行"


def test_plan_order_puts_higher_weight_first_within_a_layer() -> None:
    """同层内仍按权重降序：拓扑只负责依赖，不应把优先级拥拨掉。"""
    nodes = _plan(40)["dag_nodes"]
    for node in nodes:
        deps = [d for d in node.get("depends_on") or [] if any(n["id"] == d for n in nodes)]
        if not deps:
            continue
        position = {n["id"]: i for i, n in enumerate(nodes)}
        layer_start = max(position[d] for d in deps) + 1
        layer = nodes[layer_start : position[node["id"]]]
        weights = [n["weight"] for n in layer]
        assert weights == sorted(weights, reverse=True), f"{node[id]} 所在层未按权重降序"
