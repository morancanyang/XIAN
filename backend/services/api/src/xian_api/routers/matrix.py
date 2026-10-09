"""攻击矩阵与武器库（PRD 3.5）。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from xian_core.cases import all_cases, assert_export_allowed, get_case, next_pipeline_status
from xian_core.matrix import categories_out, coverage_for, framework_mapping, framework_names, load_categories
from xian_core.redteam.mutator import OPERATORS, op_names, safe_op_names
from xian_core.redteam.strategies import (
    load_strategies,
    render_strategy,
    strategies_for_category,
)
from xian_core.schemas.attack import AttackCaseOut, AttackCaseRenderOut, AttackCategoryOut

from ..deps import PrincipalDep

router = APIRouter(prefix="/matrix", tags=["matrix"])


@router.get("/categories", response_model=list[AttackCategoryOut])
async def categories(principal: PrincipalDep) -> list[AttackCategoryOut]:
    return categories_out()


@router.get("/coverage")
async def coverage(principal: PrincipalDep) -> dict[str, Any]:
    codes = [c.category_code for c in all_cases()]
    return {"categories": len(load_categories()), "cases": len(codes), "coverage": coverage_for(codes)}


@router.get("/frameworks")
async def frameworks(principal: PrincipalDep) -> dict[str, Any]:
    return {name: framework_mapping(name) for name in framework_names()}


@router.get("/cases", response_model=list[AttackCaseOut])
async def cases(principal: PrincipalDep, category: str | None = None, scenario: str | None = None) -> list[AttackCaseOut]:
    from xian_core.cases import select_cases

    return [c.to_out() for c in select_cases(categories=[category] if category else None, scenario=scenario, limit=200)]


@router.get("/cases/{case_id}", response_model=AttackCaseOut)
async def case_detail(case_id: str, principal: PrincipalDep) -> AttackCaseOut:
    case = get_case(case_id)
    if case is None:
        raise HTTPException(404, f"用例 {case_id} 不存在")
    return case.to_out()


@router.get("/cases/{case_id}/render", response_model=AttackCaseRenderOut)
async def render_case(case_id: str, principal: PrincipalDep) -> AttackCaseRenderOut:
    """把用例模板渲染成可直接下发的成品载荷（模式二武器库选中即填入输入框）。

    与 `/cases/{case_id}/export` 的区别：export 返回未渲染的原始模板且仅 admin
    可用；这里返回按默认变量渲染后的成品，变量未覆盖时原位保留 `{{占位符}}`。
    """
    from xian_core.cases import get_case, render_payload
    from xian_core.redteam.payload import DEFAULT_VARIABLES

    case = get_case(case_id)
    if case is None:
        raise HTTPException(404, f"用例 {case_id} 不存在")
    payload = render_payload(case.payload_template, DEFAULT_VARIABLES)
    missing = [v for v in case.variables if not str(DEFAULT_VARIABLES.get(v, "")).strip()]
    return AttackCaseRenderOut(
        case_id=case_id,
        payload=payload,
        variables=list(case.variables),
        missing=missing,
    )


@router.get("/operators")
async def operators(principal: PrincipalDep) -> dict[str, Any]:
    return {"total": len(op_names()), "safe": len(safe_op_names()), "operators": list(OPERATORS)}


@router.post("/mutate")
async def mutate_payload(body: dict, principal: PrincipalDep) -> dict[str, Any]:
    from xian_core.redteam.mutator import mutate as _mutate

    text = str(body.get("payload", ""))
    ops = list(body.get("ops", safe_op_names()[:5]))
    results = _mutate(text, ops=ops)
    return {
        "original": text,
        "results": [
            {"op": r.op, "text": r.text, "semantics_safe": r.semantics_safe}
            for r in results
        ],
    }


@router.get("/strategies")
async def strategies(principal: PrincipalDep, category: str | None = None) -> list[dict[str, Any]]:
    items = strategies_for_category(category) if category else load_strategies()
    return [{"id": s.id, "name": s.name, "categories": list(s.categories), "turns": s.turns,
             "description": s.description, "escalation": list(s.escalation)} for s in items]


@router.post("/strategies/render")
async def render(body: dict, principal: PrincipalDep) -> dict[str, Any]:
    strategy_id = str(body.get("strategy_id", ""))
    context = dict(body.get("context", {}))
    return {"strategy_id": strategy_id, "turns": render_strategy(strategy_id, context)}


@router.get("/cases/{case_id}/export")
async def export_case(case_id: str, principal: PrincipalDep) -> dict[str, Any]:
    """武器库导出管控（AC-09 后半）：非 admin 一律拒绝。"""
    case = get_case(case_id)
    if case is None:
        raise HTTPException(404, f"用例 {case_id} 不存在")
    assert_export_allowed(case, role=principal.role)
    return {"case_id": case_id, "payload": case.payload_template}


@router.post("/cases/{case_id}/review")
async def review_case(case_id: str, body: dict, principal: PrincipalDep) -> dict[str, Any]:
    """贡献评审流水线：submitted → auto_test → review → published（PRD 3.5.5.8.1）。"""
    current = str(body.get("status", "submitted"))
    return {"case_id": case_id, "status": next_pipeline_status(current, bool(body.get("passed", False)))}