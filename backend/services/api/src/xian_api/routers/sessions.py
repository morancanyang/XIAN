"""模式二：手动控制台（会话、消息、战报卡片、归档回放）（PRD 3.4.4）。"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from xian_core.db.models import BattleCard, Session, SessionMessage
from xian_core.db.repositories import BattleCardRepository, SessionMessageRepository, SessionRepository
from xian_core.schemas.session import MessageIn, MessageOut, SessionCreate, SessionOut
from xian_core.sessions import (
    Message,
    assert_session_transition,
    build_archive,
    build_session,
    card_from_verdict,
    token_guard,
)
from xian_core.sessions.executor import run_console_turn, utc_now_naive

from ..deps import PrincipalDep, SessionDep

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, session: SessionDep, principal: PrincipalDep) -> SessionOut:
    repo = SessionRepository(session, principal.tenant_id)
    row = await repo.add(
        Session(
            **build_session(
                tenant_id=principal.tenant_id,
                user_id=principal.user_id,
                agent_id=payload.agent_id,
                mode=str(payload.mode),
                goal=payload.goal,
                scenario_instance_id=payload.scenario_instance_id,
                level_id=payload.level_id,
            )
        )
    )
    await session.commit()
    await session.refresh(row)
    return SessionOut.model_validate(row)


@router.get("", response_model=list[SessionOut])
async def list_sessions(session: SessionDep, principal: PrincipalDep) -> list[SessionOut]:
    rows = await SessionRepository(session, principal.tenant_id).list()
    return [SessionOut.model_validate(r) for r in rows]


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> SessionOut:
    row = await SessionRepository(session, principal.tenant_id).get_optional(session_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")
    return SessionOut.model_validate(row)


@router.post("/{session_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    session_id: uuid.UUID, payload: MessageIn, session: SessionDep, principal: PrincipalDep
) -> MessageOut:
    """发送一条攻击消息并写入会话（判定由 worker 异步完成，PRD 3.4.4）。"""
    repo = SessionRepository(session, principal.tenant_id)
    row = await repo.get_optional(session_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")
    if row.user_id != principal.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能操作自己的会话")
    token_guard(row.tokens_used + 4000, limit=200_000)
    message = Message(role="user", content=payload.content, payload_ref=payload.case_id or "")
    saved = await SessionMessageRepository(session, principal.tenant_id).add(
        SessionMessage(
            session_id=session_id,
            role=message.role,
            content=message.content,
            payload_ref=message.payload_ref,
            # server_default 的 CURRENT_TIMESTAMP 只有秒精度，同一秒内的消息排序不稳定；
            # 这里显式写入微秒精度时间戳（与 CURRENT_TIMESTAMP 同为 UTC），保证对话顺序正确
            ts=utc_now_naive(),
        )
    )
    row.tokens_used += 4000
    row.last_activity_at = utc_now_naive()
    await session.commit()
    await session.refresh(saved)
    # 同步执行本轮自由攻击：目标应答、三级裁判与战报卡片都需在读回消息前落库
    await run_console_turn(
        session,
        session_row=row,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        payload=payload.content,
        case_id=payload.case_id,
    )
    await session.commit()
    return MessageOut.model_validate(saved)


@router.get("/{session_id}/messages", response_model=list[MessageOut])
async def list_messages(
    session_id: uuid.UUID, session: SessionDep, principal: PrincipalDep, limit: int = 50
) -> list[MessageOut]:
    rows = await SessionMessageRepository(session, principal.tenant_id).recent(session_id, limit=limit)
    return [MessageOut.model_validate(r) for r in rows]


@router.post("/{session_id}/pause", response_model=SessionOut)
async def pause_session(session_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> SessionOut:
    repo = SessionRepository(session, principal.tenant_id)
    row = await repo.get_optional(session_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")
    assert_session_transition(row.status, "paused")
    row.status = "paused"
    await session.commit()
    await session.refresh(row)
    return SessionOut.model_validate(row)


@router.post("/{session_id}/complete", response_model=SessionOut)
async def complete_session(session_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> SessionOut:
    repo = SessionRepository(session, principal.tenant_id)
    row = await repo.get_optional(session_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")
    assert_session_transition(row.status, "completed")
    row.status = "completed"
    await session.commit()
    await session.refresh(row)
    return SessionOut.model_validate(row)


@router.get("/{session_id}/archive")
async def archive_session(session_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """归档回放：会话 + 全部消息 + token 计量。"""
    repo = SessionRepository(session, principal.tenant_id)
    row = await repo.get_optional(session_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")
    messages = [
        Message(role=m.role, content=m.content, payload_ref=m.payload_ref, trace_ref=m.trace_ref, verdict=m.verdict)
        for m in await SessionMessageRepository(session, principal.tenant_id).recent(session_id, limit=500)
    ]
    return build_archive(row, messages)


@router.post("/{session_id}/cards", status_code=status.HTTP_201_CREATED)
async def create_card(
    session_id: uuid.UUID, body: dict, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """命中即生成战报卡片（PRD 3.4.4.8.1）。"""
    card = card_from_verdict(
        record_id=str(body.get("record_id", "")),
        category_code=str(body.get("category_id", "")),
        severity=str(body.get("severity", "medium")),
        payload=str(body.get("payload", "")),
        evidence=list(body.get("evidence", [])),
    )
    row = await BattleCardRepository(session, principal.tenant_id).add(
        BattleCard(
            session_id=session_id, user_id=principal.user_id, category_id=card.category_code,
            severity=card.severity, evidence=card.evidence, payload=card.payload,
        )
    )
    await session.commit()
    return {"id": str(row.id), **card.to_dict()}


@router.get("/{session_id}/cards")
async def list_cards(session_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> list[dict[str, Any]]:
    rows = await BattleCardRepository(session, principal.tenant_id).for_session(session_id)
    return [
        {"id": str(r.id), "category_id": r.category_id, "severity": r.severity,
         "evidence": list(r.evidence), "payload": r.payload}
        for r in rows
    ]
