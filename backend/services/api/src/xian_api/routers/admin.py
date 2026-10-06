"""平台管理：账号与权限、审计与防滥用、门禁规则、定时巡检（PRD 3.8.5 / 3.9）。"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from xian_core.db.models import GateRule, Member, ScanJob, User
from xian_core.db.repositories import (
    AuditRepository,
    GateRuleRepository,
    ScanJobRepository,
    UserRepository,
)
from xian_core.ops import GateRule as GateRuleSpec
from xian_core.ops import assert_rule, evaluate, to_json, to_sarif
from xian_core.schemas.report import GateRuleOut, ScanJobOut

from ..deps import Principal, PrincipalDep, SessionDep, require

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/members")
async def list_members(session: SessionDep, principal: Annotated[Principal, Depends(require("member:manage"))]) -> list[dict[str, Any]]:
    from xian_core.db.repositories import MemberRepository

    rows = await MemberRepository(session, principal.tenant_id).list()
    return [{"id": str(r.id), "user_id": str(r.user_id), "role": r.role, "status": r.status} for r in rows]


@router.post("/members")
async def add_member(
    body: dict, session: SessionDep, principal: Annotated[Principal, Depends(require("member:manage"))]
) -> dict[str, Any]:
    from xian_core.db.repositories import MemberRepository

    email = str(body.get("email", "")).strip()
    role = str(body.get("role", "viewer"))
    if role not in ("admin", "red", "blue", "viewer"):
        raise HTTPException(400, f"未知角色 {role}")
    user_repo = UserRepository(session, principal.tenant_id)
    try:
        user = await user_repo.get_by_email(email)
    except Exception:
        user = await user_repo.add(User(email=email, name=email.split("@")[0]))
    member = await MemberRepository(session, principal.tenant_id).add(
        Member(tenant_id=principal.tenant_id, user_id=user.id, role=role, status="active")
    )
    await session.commit()
    return {"id": str(member.id), "user_id": str(user.id), "role": role, "status": "active"}


@router.get("/audit-logs")
async def audit_logs(
    session: SessionDep, principal: Annotated[Principal, Depends(require("audit:read"))],
    action: str | None = None, limit: int = 100,
) -> list[dict[str, Any]]:
    rows = await AuditRepository(session, principal.tenant_id).list(size=min(limit, 500))
    return [
        {"id": str(r.id), "action": r.action, "target": r.target, "result": r.result,
         "ip": r.ip, "user_id": str(r.user_id) if r.user_id else None, "detail": r.detail}
        for r in rows if action is None or r.action == action
    ]


@router.get("/gate-rules", response_model=list[GateRuleOut])
async def list_gate_rules(session: SessionDep, principal: PrincipalDep) -> list[GateRuleOut]:
    rows = await GateRuleRepository(session, principal.tenant_id).list()
    return [GateRuleOut.model_validate(r) for r in rows]


@router.post("/gate-rules", response_model=GateRuleOut, status_code=201)
async def create_gate_rule(body: dict, session: SessionDep, principal: PrincipalDep) -> GateRuleOut:
    assert_rule(body)
    row = await GateRuleRepository(session, principal.tenant_id).add(
        GateRule(
            tenant_id=principal.tenant_id,
            name=str(body.get("name", "default")),
            max_score_drop=int(body.get("max_score_drop", 5)),
            fail_on_new_high=bool(body.get("fail_on_new_high", True)),
            min_sec_score=int(body.get("min_sec_score", 0)),
            webhook_url=str(body.get("webhook_url", "")),
        )
    )
    await session.commit()
    await session.refresh(row)
    return GateRuleOut.model_validate(row)


@router.get("/scan-jobs", response_model=list[ScanJobOut])
async def list_scan_jobs(session: SessionDep, principal: PrincipalDep) -> list[ScanJobOut]:
    rows = await ScanJobRepository(session, principal.tenant_id).list()
    return [ScanJobOut.model_validate(r) for r in rows]


@router.post("/scan-jobs", response_model=ScanJobOut, status_code=201)
async def create_scan_job(body: dict, session: SessionDep, principal: PrincipalDep) -> ScanJobOut:
    row = await ScanJobRepository(session, principal.tenant_id).add(
        ScanJob(
            tenant_id=principal.tenant_id,
            agent_id=uuid.UUID(str(body["agent_id"])),
            cadence=str(body.get("cadence", "weekly")),
            enabled=bool(body.get("enabled", True)),
        )
    )
    await session.commit()
    await session.refresh(row)
    return ScanJobOut.model_validate(row)


@router.post("/gate/evaluate")
async def evaluate_gate(body: dict, principal: PrincipalDep) -> dict[str, Any]:
    """门禁预演：把规则与指标送进来即可看到结论（PRD 3.8.5.1）。"""
    rule: GateRuleSpec = assert_rule(body.get("rule", {}))
    result = evaluate(
        rule=rule,
        current_score=int(body.get("current_score", 0)),
        previous_score=body.get("previous_score"),
        new_high_count=int(body.get("new_high_count", 0)),
        baseline_pass_rate=float(body.get("baseline_pass_rate", 1.0)),
    )
    return {"result": result.to_dict(), "json": to_json(result), "sarif": to_sarif(result)}