"""模式二会话 / 消息 / 战报卡片（PRD 3.4.4）。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import (
    GUID,
    UUIDPK,
    Base,
    JSONType,
    TenantMixin,
    timestamp_default,
)


class Session(UUIDPK, TenantMixin, Base):
    """session{id,user_id,tenant_id,agent_id,scenario_instance_id,mode,status,started_at,ended_at}"""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    scenario_instance_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    level_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), default="console", index=True)
    goal: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=timestamp_default()
    )


class SessionMessage(UUIDPK, Base):
    """session_message{id,session_id,role,content,payload_ref,trace_ref,ts}"""

    __tablename__ = "session_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), default="user")
    content: Mapped[str] = mapped_column(Text, default="")
    payload_ref: Mapped[str] = mapped_column(String(255), default="")
    trace_ref: Mapped[str] = mapped_column(String(255), default="")
    verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)


class BattleCard(UUIDPK, Base):
    """battle_card{id,session_id,category_id,severity,evidence[],payload,created_at}"""

    __tablename__ = "battle_cards"

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    category_id: Mapped[str] = mapped_column(String(16), default="")
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    evidence: Mapped[list] = mapped_column(JSONType, default=list)
    payload: Mapped[str] = mapped_column(Text, default="")
    record_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)