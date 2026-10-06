"""模式二会话：手动控制台、消息、战报卡片、归档回放（PRD 3.4.4）。"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..errors import NotFoundError, ValidationError

SESSION_TRANSITIONS: dict[str, set[str]] = {
    "active": {"paused", "completed", "aborted"},
    "paused": {"active", "aborted"},
    "completed": set(),
    "aborted": set(),
}


def assert_session_transition(current: str, target: str) -> None:
    if target not in SESSION_TRANSITIONS.get(current, set()):
        raise ValidationError(f"会话状态不允许从 {current} 迁移到 {target}")


@dataclass(slots=True)
class Message:
    role: str
    content: str
    payload_ref: str = ""
    trace_ref: str = ""
    verdict: str | None = None
    ts: datetime = field(default_factory=lambda: datetime.now().astimezone())

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "payload_ref": self.payload_ref,
            "trace_ref": self.trace_ref,
            "verdict": self.verdict,
            "ts": self.ts.isoformat(),
        }


@dataclass(slots=True)
class BattleCard:
    category_code: str
    severity: str
    evidence: list[dict[str, Any]]
    payload: str
    record_id: str | None = None
    title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "category_id": self.category_code,
            "severity": self.severity,
            "evidence": list(self.evidence),
            "payload": self.payload,
            "record_id": self.record_id,
            "title": self.title or f"{self.category_code} 战报卡片",
        }


def build_session(
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    agent_id: uuid.UUID,
    mode: str = "console",
    goal: str = "",
    scenario_instance_id: uuid.UUID | None = None,
    level_id: str | None = None,
) -> dict[str, Any]:
    if mode not in {"console", "level", "archive"}:
        raise ValidationError(f"未知会话模式 {mode}")
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "agent_id": agent_id,
        "scenario_instance_id": scenario_instance_id,
        "level_id": level_id,
        "mode": mode,
        "goal": goal,
        "status": "active",
        "tokens_used": 0,
    }


def is_level_session(session: Any) -> bool:
    return str(getattr(session, "level_id", "") or "") != ""


def can_archive(session: Any) -> bool:
    return session.status in {"completed", "aborted"}


def build_archive(session: Any, messages: Iterable[Message]) -> dict[str, Any]:
    """归档回放：会话 + 全部消息 + token 计量（PRD 3.4.4 功能清单）。"""
    rows = list(messages)
    return {
        "session_id": str(session.id),
        "agent_id": str(session.agent_id),
        "level_id": session.level_id,
        "mode": session.mode,
        "status": session.status,
        "tokens_used": session.tokens_used,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "messages": [m.to_dict() for m in rows],
    }


def card_from_verdict(
    *,
    record_id: str,
    category_code: str,
    severity: str,
    payload: str,
    evidence: Iterable[dict[str, Any]],
) -> BattleCard:
    """命中即生成战报卡片（PRD 3.4.4.8.1）。"""
    return BattleCard(
        category_code=category_code,
        severity=severity,
        evidence=list(evidence),
        payload=payload,
        record_id=record_id,
    )


def token_guard(tokens_used: int, *, limit: int) -> None:
    """会话级 token 熔断（PRD 3.4.4 异常分支：单会话超限自动暂停）。"""
    if tokens_used > limit:
        raise ValidationError(f"会话 token 用量 {tokens_used} 超过上限 {limit}，会话已自动暂停")


def resume_hint(status: str) -> str:
    return {
        "active": "会话进行中",
        "paused": "会话已暂停，可继续或归档",
        "completed": "会话已完成，可回放",
        "aborted": "会话已中止，可回放",
    }.get(status, "未知状态")


def find_session_or_404(rows: Iterable[Any]) -> Any:
    rows = list(rows)
    if not rows:
        raise NotFoundError("会话不存在或无权访问")
    return rows[0]