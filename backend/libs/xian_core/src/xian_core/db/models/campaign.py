"""战役 / 战役运行态 / 预设策略集 / 策略运行 / 变异算子（PRD 3.3）。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import GUID, UUIDPK, Base, JSONType, StringArray, TenantMixin, TimestampMixin


class Preset(TenantMixin, UUIDPK, Base):
    """preset{id,name,scope,intensity,budget_default}（快速≈20分钟/标准/全面）。"""

    __tablename__ = "presets"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[list] = mapped_column(StringArray, default=list)
    intensity: Mapped[str] = mapped_column(String(16), default="standard")
    budget_default: Mapped[dict] = mapped_column(JSONType, default=dict)
    description: Mapped[str] = mapped_column(String(255), default="")


class Campaign(UUIDPK, TenantMixin, TimestampMixin, Base):
    """campaign（PRD 2.2.4 状态机，含 tripped / env_failed）。"""

    __tablename__ = "campaigns"

    agent_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    agent_version_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    scenario_instance_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    scope: Mapped[list] = mapped_column(StringArray, default=list)
    intensity: Mapped[str] = mapped_column(String(16), default="standard")
    budget: Mapped[dict] = mapped_column(JSONType, default=dict)
    constraints: Mapped[dict] = mapped_column(JSONType, default=dict)
    judge_mode: Mapped[str] = mapped_column(String(16), default="standard")
    output_mode: Mapped[str] = mapped_column(String(16), default="summary")
    preset_id: Mapped[str] = mapped_column(String(32), default="standard")
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    sec_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(1), nullable=True)
    plan_dag: Mapped[dict] = mapped_column(JSONType, default=dict)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    partial: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CampaignRun(UUIDPK, Base):
    """campaign_run：运行态高变更字段独立成表，避免 campaign 单行热点更新。"""

    __tablename__ = "campaign_runs"

    campaign_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("campaigns.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    asr_live: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    budget_left: Mapped[int] = mapped_column(Integer, default=0)
    cases_done: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StrategyRun(UUIDPK, Base):
    """strategy_run{id,campaign_id,strategy_id,turns,escalations[],outcome}"""

    __tablename__ = "strategy_runs"

    campaign_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("campaigns.id"), nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    turns: Mapped[int] = mapped_column(Integer, default=0)
    escalations: Mapped[list] = mapped_column(JSONType, default=list)
    outcome: Mapped[str] = mapped_column(String(16), default="pending")


class MutationOp(UUIDPK, Base):
    """mutation_op{id,name,type,semantics_safe,success_rate}"""

    __tablename__ = "mutation_ops"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(32), default="lexical")
    semantics_safe: Mapped[bool] = mapped_column(default=True)
    success_rate: Mapped[float] = mapped_column(default=0.0)
    description: Mapped[str] = mapped_column(String(255), default="")