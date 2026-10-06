"""靶场场景 / 实例 / 蜜标 / 假数据（PRD 3.1）。"""

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


class Scenario(UUIDPK, TenantMixin, TimestampMixin, Base):
    """scenario{id,name,category,env_template,script,default_difficulty,status}"""

    __tablename__ = "scenarios"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="general")
    env_template: Mapped[dict] = mapped_column(JSONType, default=dict)
    script: Mapped[list] = mapped_column(StringArray, default=list)
    default_difficulty: Mapped[str] = mapped_column(String(16), default="beginner")
    monitors: Mapped[list] = mapped_column(StringArray, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="published")

    tools: Mapped[list[ScenarioTool]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan", lazy="selectin"
    )
    canaries: Mapped[list[ScenarioCanary]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan", lazy="selectin"
    )


class ScenarioTool(UUIDPK, Base):
    """scenario_tool{name,scope(r/w/exec/network),risk_level,require_confirm}"""

    __tablename__ = "scenario_tools"

    scenario_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scenarios.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), default="read")
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    require_confirm: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(Text, default="")

    scenario: Mapped[Scenario] = relationship(back_populates="tools")


class ScenarioCanary(TenantMixin, UUIDPK, Base):
    """scenario_canary{id,type(key/phone/id/order),value,plant_location,instance_id,status}"""

    __tablename__ = "scenario_canaries"

    scenario_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scenarios.id"), nullable=False, index=True)
    instance_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(16), default="key")
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    plant_location: Mapped[list] = mapped_column(StringArray, default=list)
    status: Mapped[str] = mapped_column(String(16), default="planted")

    scenario: Mapped[Scenario] = relationship(back_populates="canaries")


class ScenarioInstance(UUIDPK, TenantMixin, TimestampMixin, Base):
    """scenario_instance{id,scenario_id,tenant_id,seed_data_snapshot,status,created_at,expired_at}"""

    __tablename__ = "scenario_instances"

    scenario_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scenarios.id"), nullable=False, index=True)
    seed_data_snapshot: Mapped[dict] = mapped_column(JSONType, default=dict)
    data_scale: Mapped[int] = mapped_column(Integer, default=200)
    language: Mapped[str] = mapped_column(String(16), default="zh-CN")
    canary_enhanced: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(16), default="ready", index=True)
    compose_project: Mapped[str] = mapped_column(String(128), default="")
    baseline_pass_rate: Mapped[float] = mapped_column(default=0.0)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CanaryHit(TenantMixin, UUIDPK, Base):
    """canary_hit{id,canary_id,via(output/egress),trace_ref,ts}"""

    __tablename__ = "canary_hits"

    canary_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scenario_canaries.id"), nullable=False, index=True)
    instance_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    via: Mapped[str] = mapped_column(String(16), default="output")
    trace_ref: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[dict] = mapped_column(JSONType, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class SeedDataset(TenantMixin, UUIDPK, Base):
    """seed_dataset{id,scenario_id,rules,snapshot_ref}"""

    __tablename__ = "seed_datasets"

    scenario_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("scenarios.id"), nullable=False, index=True)
    rules: Mapped[dict] = mapped_column(JSONType, default=dict)
    snapshot_ref: Mapped[str] = mapped_column(String(255), default="")
    generator_version: Mapped[str] = mapped_column(String(32), default="1.0.0")


class CustomScenario(UUIDPK, TenantMixin, TimestampMixin, Base):
    """custom_scenario{id,tenant_id,dsl_version,env_ref,tools[],canaries[],monitors[],status}"""

    __tablename__ = "custom_scenarios"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    dsl_version: Mapped[str] = mapped_column(String(16), default="1.0")
    env_ref: Mapped[str] = mapped_column(String(255), default="")
    tools: Mapped[list] = mapped_column(JSONType, default=list)
    canaries: Mapped[list] = mapped_column(JSONType, default=list)
    monitors: Mapped[list] = mapped_column(StringArray, default=list)
    status: Mapped[str] = mapped_column(String(16), default="draft")