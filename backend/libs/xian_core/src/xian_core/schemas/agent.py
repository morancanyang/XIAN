"""Agent 资产 / 版本 / 画像 / 归属校验契约（PRD 3.2）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field

from .common import (
    AccessType,
    AgentStatus,
    Difficulty,
    OwnershipMethod,
    OwnershipResult,
    StrictModel,
)


class BaselineDeclaration(StrictModel):
    """防护基线声明（PRD 3.2.4.1）。"""

    has_guardrail: bool = False
    guardrail_vendor: str = ""
    tool_scope: str = "read"
    network_enabled: bool = False
    has_rag: bool = False
    has_long_term_memory: bool = False


class AgentCreate(StrictModel):
    name: str = Field(min_length=1, max_length=128)
    access_type: AccessType
    endpoint: str = Field(min_length=1)
    description: str = ""
    baseline_declaration: BaselineDeclaration = Field(default_factory=BaselineDeclaration)


class AgentUpdate(StrictModel):
    name: str | None = None
    endpoint: str | None = None
    description: str | None = None
    baseline_declaration: BaselineDeclaration | None = None
    status: AgentStatus | None = None


class AgentOut(StrictModel):
    id: UUID
    tenant_id: UUID
    name: str
    access_type: AccessType
    endpoint: str
    description: str
    ownership_verified: bool
    ownership_method: OwnershipMethod | None = None
    baseline_declaration: dict[str, Any]
    status: AgentStatus
    created_at: datetime
    updated_at: datetime | None = None


class CredentialOut(StrictModel):
    id: UUID
    agent_id: UUID
    token_hint: str
    scope: str
    revoked: bool
    created_at: datetime
    expires_at: datetime | None = None


class VerificationRequest(StrictModel):
    method: OwnershipMethod
    target: str = Field(description="域名（DNS TXT）或镜像引用（image@sha256:...）")


class VerificationRecordOut(StrictModel):
    id: UUID
    agent_id: UUID
    method: OwnershipMethod
    target: str
    nonce: str
    result: OwnershipResult
    detail: str
    ts: datetime


class HealthCheckOut(StrictModel):
    id: UUID
    agent_id: UUID
    latency_ms: int
    trace_sample: list[dict[str, Any]]
    result: str
    ts: datetime


class AgentVersionCreate(StrictModel):
    prompt_hash: str | None = None
    tools_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    model_params: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"


class AgentVersionOut(StrictModel):
    id: UUID
    agent_id: UUID
    prompt_hash: str
    tools_snapshot: list[dict[str, Any]]
    # DB 列名是 model_config，契约字段名是 model_params：两条都认，避免 model_validate 直接失败
    model_params: dict[str, Any] = Field(
        validation_alias=AliasChoices("model_params", "model_config"), default_factory=dict
    )
    diff_summary: dict[str, Any]
    source: str
    created_at: datetime


class AgentProfileOut(StrictModel):
    """侦察兵六件套产物（PRD 3.3.5.8.2）。"""

    id: UUID
    agent_id: UUID
    tools: list[dict[str, Any]] = Field(default_factory=list)
    risk_levels: dict[str, str] = Field(default_factory=dict)
    refusal_boundary: str = ""
    prompt_fragments: list[str] = Field(default_factory=list)
    fingerprint: dict[str, Any] = Field(default_factory=dict)
    latency_p50: int = 0
    latency_p99: int = 0
    lang_prefs: list[str] = Field(default_factory=list)
    created_at: datetime


class ChangeSignalOut(StrictModel):
    id: UUID
    agent_id: UUID
    kind: str
    diff_preview: dict[str, Any]
    handled: bool
    ts: datetime


class ScenarioRecommendation(StrictModel):
    """3.1.4.8.1 场景推荐：match_score, matched_tools[], reason。"""

    scenario_id: UUID
    scenario_code: str
    name: str
    difficulty: Difficulty
    match_score: float
    matched_tools: list[str]
    reason: str