"""指挥官：战役计划 DAG 生成（PRD 3.3.5.8.1）。

计划规则：
① 攻击面暴露越大优先级越高（shell > network > write > read；RAG/长期记忆加权）；
② 历史成功手法加权、连续失败手法降权或更换变异算子；
③ 阶段间设依赖（提权/渗出类依赖前序已泄露的上下文），无依赖用例并发执行；
④ 熔断规则内置于计划。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..cases import cases_by_category
from ..matrix import load_categories, normalize_stage
from ..schemas.campaign import Budget, DagNode
from ..schemas.common import Intensity

STAGE_ORDER = ["recon", "initial_exec", "payload_delivery", "privilege_escalation", "exfiltration", "impact"]

ATTACK_SURFACE_SCORE = {
    "工具层": 1.5,
    "多智能体层": 1.4,
    "MCP/插件/依赖": 1.35,
    "记忆层/RAG": 1.3,
    "数据层/工具层": 1.25,
    "输出/下游": 1.15,
    "运行时": 1.0,
    "模型层": 0.95,
    "会话层": 0.9,
    "工具返回值/RAG/网页/邮件/文档": 1.2,
    "图片/PDF/语音": 1.1,
    "提示词层": 0.8,
}

INTENSITY_PROFILE = {
    Intensity.recon: {"budget_factor": 0.4, "max_turns": 2, "ops_per_case": 1, "strategies": False},
    Intensity.standard: {"budget_factor": 1.0, "max_turns": 3, "ops_per_case": 2, "strategies": True},
    Intensity.deep: {"budget_factor": 2.0, "max_turns": 5, "ops_per_case": 3, "strategies": True},
}


@dataclass(slots=True)
class AgentSurface:
    """侦察兵产出的攻击面摘要，供指挥官排序。"""

    has_shell: bool = False
    has_network: bool = False
    has_write: bool = False
    has_rag: bool = False
    has_memory: bool = False
    has_multi_agent: bool = False
    tools: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HistorySignal:
    """历史战役记忆：成功手法加权、连续失败手法降权（PRD 3.3.5.8.1 规则②）。"""

    category_success: dict[str, float] = field(default_factory=dict)
    category_streak_fail: dict[str, int] = field(default_factory=dict)


def attack_surface_priority(category_code: str, surface: AgentSurface) -> float:
    """规则①：攻击面暴露越大优先级越高。"""
    cat = next((c for c in load_categories() if c.code == category_code), None)
    base = ATTACK_SURFACE_SCORE.get(cat.attack_surface, 1.0) if cat else 1.0
    tools_text = " ".join(surface.tools).lower()
    if surface.has_shell and any(k in tools_text for k in ("shell", "exec", "command")):
        base *= 1.6
    elif surface.has_network:
        base *= 1.25
    elif surface.has_write:
        base *= 1.15
    if surface.has_rag and category_code in ("XM-02", "XM-06"):
        base *= 1.3
    if surface.has_memory and category_code in ("XM-06",):
        base *= 1.35
    if surface.has_multi_agent and category_code == "XM-10":
        base *= 1.4
    return round(base, 4)


def _weight(category_code: str, surface: AgentSurface, history: HistorySignal) -> float:
    weight = attack_surface_priority(category_code, surface)
    weight *= 1.0 + history.category_success.get(category_code, 0.0)
    weight *= 1.0 / (1.0 + 0.2 * history.category_streak_fail.get(category_code, 0))
    return round(max(weight, 0.05), 4)


def _topological_order(nodes: list[DagNode]) -> list[DagNode]:
    """Kahn 拓扑排序：依赖先行，同层内按权重降序。

    规则③要求提权/渗出等前序上下文就位；节点原先按权重降序平铺，
    依赖只画在图上，执行时该等的没等——提权用例会在侦察结果之前就跑完。
    """
    by_id = {node.id: node for node in nodes}
    pending = {node.id: set(node.depends_on) & set(by_id) for node in nodes}
    ordered: list[DagNode] = []
    while pending:
        ready = [by_id[nid] for nid, deps in pending.items() if not deps]
        if not ready:
            # 依赖成环时不能把战役卡死：按权重强制收尾
            stuck = max(pending, key=lambda nid: by_id[nid].weight)
            ready = [by_id[stuck]]
        ready.sort(key=lambda node: -node.weight)
        chosen = ready[0]
        ordered.append(chosen)
        del pending[chosen.id]
        for deps in pending.values():
            deps.discard(chosen.id)
    return ordered


def build_plan(
    *,
    scope: list[str],
    intensity: Intensity,
    budget: Budget,
    surface: AgentSurface | None = None,
    history: HistorySignal | None = None,
) -> dict[str, Any]:
    """生成战役计划 DAG（阶段 -> 类别 -> 用例集 -> 预算分配）。"""
    surface = surface or AgentSurface()
    history = history or HistorySignal()
    profile = INTENSITY_PROFILE.get(intensity, INTENSITY_PROFILE[Intensity.standard])

    categories = sorted(
        (c for c in load_categories() if c.code in scope),
        key=lambda c: -_weight(c.code, surface, history),
    )
    # 预算比类别数还小时只保留权重最高的若干类：每类至少 1 条是用例底线，
    # 否则后面 max(1, ...) 会把预算撑爆，DAG 上的用例总数和 budget.cases 对不上。
    if 0 < budget.cases < len(categories):
        categories = categories[:budget.cases]
    nodes: list[DagNode] = []
    edges: list[list[str]] = []
    for cat in categories:
        nodes.append(
            DagNode(
                id=cat.code,
                category_code=cat.code,
                stage=_stage_of(cat.stage),
                case_ids=[],
                budget_split={},
                weight=_weight(cat.code, surface, history),
            )
        )
    # 依赖必须在全部节点入列后统一计算：边只跟"阶段/类别"有关，
    # 不该被权重排序偶然决定（否则同一份 scope 换个顺序就画出不同的 DAG）。
    for node in nodes:
        node.depends_on = _depends_on(node.stage, node.category_code, [n.id for n in nodes if n.id != node.id])
        for dep in node.depends_on:
            edges.append([dep, node.id])


    # 执行顺序必须是拓扑序：提权/渗出类要等前序上下文就位（规则③）。
    # 节点列表同时是详情页 DAG 的渲染顺序与执行器的取用例顺序，
    # 在这里排好，图上的箭头才和实际跑序一致。
    nodes = _topological_order(nodes)
    total_weight = sum(n.weight for n in nodes) or 1.0
    scaled_token = int(budget.token * profile["budget_factor"])
    # 权重比例直接取整会丢份额，max(1, ...) 又会向上溢出，
    # DAG 上的用例总数于是既不等于预算也可能超支。
    # 这里用最大余额法把 cases 整数分完，
    # 让 DAG 的用例总数恰好等于 budget.cases，执行器才能照单执行。
    shares = [budget.cases * node.weight / total_weight for node in nodes]
    allocation = [max(1, int(share)) for share in shares]
    leftover = budget.cases - sum(allocation)
    if leftover > 0:
        by_remainder = sorted(range(len(nodes)), key=lambda idx: -(shares[idx] - int(shares[idx])))
        for idx in by_remainder[:leftover]:
            allocation[idx] += 1
    elif leftover < 0:
        by_share = sorted(range(len(nodes)), key=lambda idx: shares[idx])
        cursor = 0
        while leftover < 0 and cursor < len(by_share):
            idx = by_share[cursor]
            if allocation[idx] > 1:
                allocation[idx] -= 1
                leftover += 1
            else:
                cursor += 1
    # 类别里的用例可能不够分：把超出可用量的份额回收，再按权重分给还有余量的类别。
    # 不锡的话 DAG 的用例总数会大于实际能跑的条数，执行清单又不准了。
    available = {node.category_code: len(cases_by_category(node.category_code)) for node in nodes}
    allocation = [min(count, available[node.category_code]) for node, count in zip(nodes, allocation)]
    remaining = budget.cases - sum(allocation)
    while remaining > 0:
        headroom = [
            idx
            for idx in sorted(range(len(nodes)), key=lambda i: -shares[i])
            if allocation[idx] < available[nodes[idx].category_code]
        ]
        if not headroom:
            break
        allocation[headroom[0]] += 1
        remaining -= 1
    for node, cases, share in zip(nodes, allocation, shares):
        node.budget_split = {
            "token": int(scaled_token * round(node.weight / total_weight, 4)),
            "cases": cases,
            "max_turns": profile["max_turns"],
        }
        # 节点上带出该类别实际会跑的用例：DAG 不只是几张卡片，而是可核对的执行清单
        node.case_ids = [c.case_id for c in cases_by_category(node.category_code)][:cases]
    return {
        "dag_nodes": [n.model_dump(mode="json") for n in nodes],
        "edges": edges,
        "budget_split": {n.id: n.budget_split for n in nodes},
        "constraints": {"max_turns": profile["max_turns"], "ops_per_case": profile["ops_per_case"],
                        "strategies": profile["strategies"]},
        "surface_priority": {n.id: n.weight for n in nodes},
    }


def _stage_of(raw_stage: str) -> str:
    """类别声明的 stage 文本 -> 规范阶段键（六段）。

    归一规则统一放在 matrix.catalog：报告的攻击路径图要用同一份类别阶段
    收敛成五段 kill chain，两边各写一张码表必然对不上。
    """
    return normalize_stage(raw_stage)


def _depends_on(stage: str, category_code: str, existing: list[str]) -> list[str]:
    """规则③：提权/渗出类依赖前序已泄露上下文；无依赖用例可并发。"""
    if stage == "exfiltration":
        return [n for n in existing if n in ("XM-03", "XM-13")]
    if stage == "privilege_escalation":
        return [n for n in existing if n in ("XM-01", "XM-03", "XM-11")]
    if stage == "impact" and category_code == "XM-10":
        return [n for n in existing if n in ("XM-01", "XM-06")]
    return []