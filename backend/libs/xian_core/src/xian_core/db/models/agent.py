"""Agent 资产 / 凭证 / 版本 / 画像 / 归属校验（PRD 3.2）。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import (
    GUID,
    UUIDPK,
    Base,
    JSONType,
    StringArray,
    TenantMixin,
    TimestampMixin,
    timestamp_default,
)


class Agent(UUIDPK, TenantMixin, TimestampMixin, Base):
    """agent{id,tenant_id,name,access_type,endpoint,ownership_verified,baseline_declaration,status}

    状态机：unverified → active ⇄ testing / offline → archived（技术方案 2.2）。
    """

    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    access_type: Mapped[str] = mapped_column(String(16), default="http")
    endpoint: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    ownership_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    ownership_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    baseline_declaration: Mapped[dict] = mapped_column(JSONType, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="unverified", index=True)

    versions: Mapped[list[AgentVersion]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    profiles: Mapped[list[AgentProfile]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    credentials: Mapped[list[AgentCredential]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class AgentCredential(TenantMixin, UUIDPK, Base):
    """agent_credential{token,scope,expired_at}：加密列，支持轮换与撤销。"""

    __tablename__ = "agent_credentials"

    agent_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("agents.id"), nullable=False, index=True)
    token_encrypted: Mapped[str] = mapped_column(Text, default="")
    scope: Mapped[str] = mapped_column(String(64), default="attack")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent: Mapped[Agent] = relationship(back_populates="credentials")


class AgentVersion(UUIDPK, Base):
    """agent_version{id,agent_id,prompt_hash,tools_snapshot,model_config,diff_summary,source,created_at}"""

    __tablename__ = "agent_versions"

    agent_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("agents.id"), nullable=False, index=True)
    prompt_hash: Mapped[str] = mapped_column(String(64), default="")
    tools_snapshot: Mapped[list] = mapped_column(JSONType, default=list)
    model_config: Mapped[dict] = mapped_column(JSONType, default=dict)
    diff_summary: Mapped[dict] = mapped_column(JSONType, default=dict)
    source: Mapped[str] = mapped_column(String(16), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)

    agent: Mapped[Agent] = relationship(back_populates="versions")


class AgentProfile(TenantMixin, UUIDPK, Base):
    """agent_profile{tools[],risk_levels,refusal_boundary,prompt_fragments[],fingerprint,latency_p50/p99,lang_prefs}"""

    __tablename__ = "agent_profiles"

    agent_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("agents.id"), nullable=False, index=True)
    tools: Mapped[list] = mapped_column(JSONType, default=list)
    risk_levels: Mapped[dict] = mapped_column(JSONType, default=dict)
    refusal_boundary: Mapped[str] = mapped_column(Text, default="")
    prompt_fragments: Mapped[list] = mapped_column(JSONType, default=list)
    fingerprint: Mapped[dict] = mapped_column(JSONType, default=dict)
    latency_p50: Mapped[int] = mapped_column(Integer, default=0)
    latency_p99: Mapped[int] = mapped_column(Integer, default=0)
    lang_prefs: Mapped[list] = mapped_column(StringArray, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())

    agent: Mapped[Agent] = relationship(back_populates="profiles")


class VerificationRecord(TenantMixin, UUIDPK, Base):
    """verification_record{type(dns/image),target,nonce,result,ts}"""

    __tablename__ = "verification_records"

    agent_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("agents.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), default="dns_txt")
    target: Mapped[str] = mapped_column(String(512), default="")
    nonce: Mapped[str] = mapped_column(String(128), default="")
    result: Mapped[str] = mapped_column(String(16), default="failed")
    detail: Mapped[str] = mapped_column(Text, default="")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class HealthCheck(TenantMixin, UUIDPK, Base):
    """health_check{id,agent_id,latency_ms,trace_sample,result,ts}"""

    __tablename__ = "health_checks"

    agent_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("agents.id"), nullable=False, index=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    trace_sample: Mapped[list] = mapped_column(JSONType, default=list)
    result: Mapped[str] = mapped_column(String(32), default="ok")
    detail: Mapped[str] = mapped_column(Text, default="")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class ChangeSignal(TenantMixin, UUIDPK, Base):
    """change_signal{id,agent_id,kind,diff_preview,ts,handled}"""

    __tablename__ = "change_signals"

    agent_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("agents.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), default="prompt")
    diff_preview: Mapped[dict] = mapped_column(JSONType, default=dict)
    handled: Mapped[bool] = mapped_column(Boolean, default=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())