"""攻击记录、判定与 trace 回放（PRD 3.3.6 / 3.6.4）。"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from xian_core.db.models import Verdict
from xian_core.db.repositories import AttackRecordRepository, VerdictRepository
from xian_core.judge import JudgeContext, JudgeEngine
from xian_core.schemas.attack import AttackRecordOut, VerdictOut
from xian_core.schemas.common import Page, PageParams
from xian_core.storage import ClickHouseStore

from ..deps import PrincipalDep, SessionDep

router = APIRouter(tags=["records"])


@router.get("/campaigns/{campaign_id}/records", response_model=Page[AttackRecordOut])
async def list_records(
    campaign_id: uuid.UUID, session: SessionDep, principal: PrincipalDep, page: PageParams = Depends()
) -> Page[AttackRecordOut]:
    repo = AttackRecordRepository(session, principal.tenant_id)
    rows = await repo.list_by(campaign_id=campaign_id)
    total = len(rows)
    start = (page.page - 1) * page.size
    items = [AttackRecordOut.model_validate(r) for r in rows[start : start + page.size]]
    return Page(items=items, total=total, page=page.page, size=page.size)


@router.get("/records/{record_id}", response_model=AttackRecordOut)
async def get_record(record_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> AttackRecordOut:
    repo = AttackRecordRepository(session, principal.tenant_id)
    row = await repo.get_optional(record_id)
    if row is None:
        raise HTTPException(404, "攻击记录不存在")
    return AttackRecordOut.model_validate(row)


@router.get("/records/{record_id}/trace", response_model=dict)
async def get_trace(record_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """trace 回放：完整请求/响应/工具调用/判定过程（PRD 3.3.6.4）。"""
    repo = AttackRecordRepository(session, principal.tenant_id)
    record = await repo.get_optional(record_id)
    if record is None:
        raise HTTPException(404, "攻击记录不存在")
    store = ClickHouseStore()
    events = await store.query_by_record(principal.tenant_id, record_id)
    verdicts = await VerdictRepository(session, principal.tenant_id).list_by(record_id=record_id)
    return {
        "record_id": str(record_id),
        "campaign_id": str(record.campaign_id) if record.campaign_id else None,
        "session_id": str(record.session_id) if record.session_id else None,
        "case_id": record.case_id,
        "category_code": record.category_code,
        "strategy": record.strategy,
        "mutation_ops": list(record.mutation_ops or []),
        "trace_key": record.trace_key,
        "events": events,
        "tokens": record.tokens,
        "cost": record.cost,
        "rule_hits": list(record.rule_hits or []),
        "evidence": list(record.evidence or []),
        "verdicts": [VerdictOut.model_validate(v) for v in verdicts],
    }


@router.post("/records/{record_id}/adjudicate", response_model=VerdictOut)
async def adjudicate(record_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> VerdictOut:
    """人工/离线复判：对单条记录重跑三级裁判（PRD 3.3.6.4 / 3.6.4）。"""
    repo = AttackRecordRepository(session, principal.tenant_id)
    record = await repo.get_optional(record_id)
    if record is None:
        raise HTTPException(404, "攻击记录不存在")
    events = await ClickHouseStore().query_by_record(principal.tenant_id, record_id)
    engine = JudgeEngine()
    outcome = await engine.adjudicate(
        events=events,
        context=JudgeContext(
            output_text="\n".join(str(e.get("result", "")) for e in events),
            canary_values=[str(h.get("canary_id", "")) for h in record.rule_hits or []],
        ),
    )
    row = await VerdictRepository(session, principal.tenant_id).add(
        Verdict(
            record_id=record_id,
            level=str(outcome.level),
            result=str(outcome.verdict),
            confidence=outcome.confidence,
            rule_hits=list(outcome.rule_hits),
            evidence=list(outcome.evidence),
            judge_model=outcome.judge_model,
            reason=outcome.reason,
        )
    )
    record.verdict = str(outcome.verdict)
    record.confidence = outcome.confidence
    record.rule_hits = list(outcome.rule_hits)
    record.evidence = list(outcome.evidence)
    await session.commit()
    await session.refresh(row)
    return VerdictOut.model_validate(row)
