"""WS/SSE 事件契约（技术方案 6.6）。

频道：``campaign:{id}`` 与 ``sessions:{session_id}`` 复用同一 schema；
mode=console 时在 ``type`` 中扩展 ``battle_card`` / ``hint_used`` / ``energy`` / ``level_progress``。
前端 ``packages/types/src/events.ts`` 由该契约生成联合类型。
"""

from __future__ import annotations

import enum
from typing import Any, Literal

from pydantic import Field

from .common import StrictModel

EventType = Literal[
    "log",
    "tool_call",
    "verdict",
    "progress",
    "alert",
    "done",
    "battle_card",
    "hint_used",
    "energy",
    "level_progress",
]

EventRole = Literal[
    "commander",
    "recon",
    "payload",
    "attacker",
    "mutator",
    "judge",
    "reporter",
    "system",
]


class BusEvent(StrictModel):
    """WS/SSE 事件唯一 schema。"""

    ts: int = Field(description="epoch millis")
    type: EventType
    role: EventRole = "system"
    message: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    campaign_id: str | None = None
    session_id: str | None = None


class Channel(enum.StrEnum):
    campaign = "campaign"
    session = "session"

    def name_for(self, subject_id: str) -> str:
        return f"{self.value}:{subject_id}"