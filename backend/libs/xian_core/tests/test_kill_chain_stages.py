"""kill chain 阶段必须单一出处：报告攻击路径与战役 DAG 不能各说各话。

背景：remediation.build_attack_path 里手写了一张 XM-xx -> stage 的码表，
和 categories.yaml 里类别声明的 stage 对不上——14 类里 11 类报错阶段。
XM-05（敏感数据渗出）被算成"投递"，XM-13（模型与提示词逆向，侦察）被算成"渗出"，
XM-08/09/12（影响）被算成提权或投递。报告的 kill chain 于是和 DAG 阶段列矛盾，
"断裂阶段"也判错。现在两边都从 matrix.catalog 的同一份归一规则推导。
"""

from __future__ import annotations

from xian_core.matrix import (
    KILL_CHAIN_STAGES,
    kill_chain_stage,
    load_categories,
    stage_of_category,
)
from xian_core.redteam.commander import build_plan
from xian_core.redteam.dag import topological_order
from xian_core.remediation import build_attack_path
from xian_core.schemas.campaign import Budget
from xian_core.schemas.common import Intensity

ALL_CATEGORIES = [c.code for c in load_categories()]


def _record(case_id: str, category: str, verdict: str = "success") -> dict:
    return {
        "record_id": case_id,
        "category_code": category,
        "case_id": case_id,
        "case_title": f"用例 {case_id}",
        "severity": "high",
        "verdict": verdict,
        "confidence": 0.9,
        "golden_rules": [],
        "evidence": [],
        "trace_ref": f"ch://trace/{case_id}",
    }


def test_every_category_maps_into_the_five_stage_kill_chain() -> None:
    """14 类必须全部落进 PRD 的五段 kill chain，不能有漏网阶段键。"""
    for cat in load_categories():
        stage = stage_of_category(cat.code)
        assert stage in KILL_CHAIN_STAGES, f"{cat.code} 归出非法阶段 {stage}"


def test_report_stage_equals_dag_stage_collapsed() -> None:
    """报告的阶段必须等于 DAG 阶段收敛后的结果，两边同源。"""
    for cat in load_categories():
        assert stage_of_category(cat.code) == kill_chain_stage(cat.stage), cat.code


def test_categories_cover_all_five_stages() -> None:
    """五段都得有类别落在里面，否则报告的阶段徽标永远有一列空着。"""
    used = {stage_of_category(code) for code in ALL_CATEGORIES}
    assert used == set(KILL_CHAIN_STAGES), f"只覆盖到 {sorted(used)}"


def test_recon_categories_are_not_counted_as_exfiltration() -> None:
    """锁死旧码表最严重的两处错报：侦察类不能算成渗出/投递。"""
    for code in ("XM-03", "XM-13"):
        assert stage_of_category(code) == "recon", code
    assert stage_of_category("XM-05") == "exfiltration"


def test_attack_path_stages_agree_with_dag_plan() -> None:
    """同一批类别，报告攻击路径的阶段必须和 DAG 计划里的阶段列一致（收敛后）。"""
    plan = build_plan(
        scope=ALL_CATEGORIES,
        intensity=Intensity.standard,
        budget=Budget(token=200000, cases=60, minutes=30),
    )
    dag_stage = {node["id"]: node["stage"] for node in plan["dag_nodes"]}

    records = [_record(f"{code}-001", code) for code in ALL_CATEGORIES]
    path = build_attack_path(subject_type="campaign", subject_id="c-1", records=records)

    by_category = {}
    for node in path["nodes"]:
        if node["id"].startswith("gap-"):
            continue
        by_category[str(node["label"]).removeprefix("用例 ").rsplit("-", 1)[0]] = node["stage"]
    for code, stage in by_category.items():
        assert stage == kill_chain_stage(dag_stage[code]), f"{code}: 报告 {stage} vs DAG {dag_stage[code]}"


def test_attack_path_has_no_missing_stage_when_all_categories_hit() -> None:
    """全部类别都命中时不该再有断裂阶段，也不该出现 gap 占位节点。"""
    records = [_record(f"{code}-001", code) for code in ALL_CATEGORIES]
    path = build_attack_path(subject_type="campaign", subject_id="c-1", records=records)
    assert path["missing_stages"] == []
    assert not [n for n in path["nodes"] if str(n["id"]).startswith("gap-")]
    assert set(path["kill_chain"]) == set(KILL_CHAIN_STAGES)


def test_dag_stage_order_is_a_valid_topological_order() -> None:
    """计划节点顺序仍是拓扑序：阶段归一提炼不能把依赖顺序弄坏。"""
    plan = build_plan(
        scope=ALL_CATEGORIES,
        intensity=Intensity.standard,
        budget=Budget(token=200000, cases=40, minutes=30),
    )
    order = topological_order(plan)
    nodes = {n["id"]: n for n in plan["dag_nodes"]}
    position = {node_id: index for index, node_id in enumerate(order)}
    for node in nodes.values():
        for dep in node.get("depends_on") or []:
            if dep in nodes:
                assert position[dep] < position[node["id"]], f"{dep} 未排在 {node[id]} 之前"
    assert len(order) == len(nodes)
    # 队首必须是零依赖节点，否则第一层就有用例在等还没打到的前序上下文
    first = nodes[order[0]]
    assert not [d for d in (first.get("depends_on") or []) if d in nodes], first["id"]
