"""攻击记录 / 判定 / 用例契约（PRD 3.3、3.5、3.6）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from .common import (
    Difficulty,
    JudgeLevel,
    Severity,
    StrictModel,
    Verdict,
)


class AttackCaseCreate(StrictModel):
    """7.4 攻击用例格式。"""

    id: str = Field(description="用例编号，如 XM-04-007")
    category_id: str = Field(description="XM-xx")
    title: str
    payload_template: str
    variables: list[str] = Field(default_factory=list)
    scenario_tags: list[str] = Field(default_factory=list)
    difficulty: Difficulty = Difficulty.medium
    severity: Severity = Severity.high
    success_criteria: dict[str, Any] = Field(default_factory=dict)
    judge_prompt: str = ""
    success_rate: float = 0.0
    status: str = "published"
    version: int = 1
    contributor: str = "platform"


class AttackCaseOut(StrictModel):
    id: str
    category_id: str
    title: str
    payload_template: str
    variables: list[str]
    scenario_tags: list[str]
    difficulty: Difficulty
    severity: Severity
    success_criteria: dict[str, Any]
    judge_prompt: str
    success_rate: float
    status: str
    version: int
    contributor: str


class AttackCategoryOut(StrictModel):
    id: str
    code: str
    name: str
    stage: str
    attack_surface: str
    difficulty: Difficulty
    impact: str
    techniques: list[str]
    detection_signals: list[str]
    owasp_ref: list[str]
    atlas_ref: list[str]


class AttackRecordOut(StrictModel):
    id: UUID
    tenant_id: UUID
    agent_id: UUID
    agent_version_id: UUID | None = None
    campaign_id: UUID | None = None
    session_id: UUID | None = None
    case_id: str
    category_code: str
    strategy: str
    mutation_ops: list[str]
    turns: int
    verdict: Verdict
    confidence: float
    rule_hits: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    tokens: int
    cost: float
    trace_key: str
    created_at: datetime


class VerdictOut(StrictModel):
    id: UUID
    record_id: UUID
    level: JudgeLevel
    result: Verdict
    confidence: float
    rule_hits: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    judge_model: str
    reason: str = ""
    ts: datetime


class TraceEventIn(StrictModel):
    """观测事件上报契约（PRD 3.4.4.8.2）。"""

    subject_id: UUID
    session_id: UUID | None = None
    event_type: str = Field(description="llm_call/tool_call/output/egress/guardrail/token")
    actor: str = "aut"
    name: str = ""
    args: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    tokens: int = 0
    canary_hit: bool = False
    latency_ms: int = 0


class TraceEventOut(TraceEventIn):
    id: UUID
    tenant_id: UUID
    ts: datetime