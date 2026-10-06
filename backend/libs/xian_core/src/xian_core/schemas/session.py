"""模式二会话 / 消息 / 战报契约（PRD 3.4.4）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from .common import SessionMode, SessionStatus, Severity, StrictModel


class SessionCreate(StrictModel):
    agent_id: UUID
    scenario_instance_id: UUID | None = None
    mode: SessionMode = SessionMode.console
    level_id: str | None = None
    goal: str = ""


class SessionOut(StrictModel):
    id: UUID
    user_id: UUID
    tenant_id: UUID
    agent_id: UUID
    scenario_instance_id: UUID | None = None
    mode: SessionMode
    level_id: str | None = None
    goal: str
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None = None


class MessageIn(StrictModel):
    content: str = Field(min_length=1)
    case_id: str | None = Field(default=None, description="来自武器库模板时带出 payload_ref")


class MessageOut(StrictModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    payload_ref: str | None = None
    trace_ref: str | None = None
    ts: datetime


class BattleCardOut(StrictModel):
    id: UUID
    session_id: UUID
    category_id: str
    severity: Severity
    evidence: list[dict[str, Any]]
    payload: str
    created_at: datetime