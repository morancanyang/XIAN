"""关卡教案 / 进度 / 提示 / 徽章 / 段位（PRD 3.4.5）。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import (
    GUID,
    UUIDPK,
    Base,
    JSONType,
    StringArray,
    TenantMixin,
    timestamp_default,
)


class Level(TenantMixin, UUIDPK, Base):
    """level{id,name,scenario_id,goal,pass_criteria,techniques[],h1,h2,h3,unlock_rule}"""

    __tablename__ = "levels"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    scenario_code: Mapped[str] = mapped_column(String(16), default="S1")
    goal: Mapped[str] = mapped_column(String(512), default="")
    pass_criteria: Mapped[dict] = mapped_column(JSONType, default=dict)
    techniques: Mapped[list] = mapped_column(StringArray, default=list)
    h1: Mapped[str] = mapped_column(String(512), default="")
    h2: Mapped[str] = mapped_column(String(512), default="")
    h3: Mapped[str] = mapped_column(String(1024), default="")
    unlock_rule: Mapped[str] = mapped_column(String(128), default="previous_passed")
    difficulty: Mapped[str] = mapped_column(String(16), default="easy")
    order_idx: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="published")


class LevelProgress(UUIDPK, Base):
    """level_progress{id,user_id,level_id,status,score,time_used,hints_used,energy_left,dimension_coverage,badge}"""

    __tablename__ = "level_progress"
    __table_args__ = ({"sqlite_autoincrement": True},)

    user_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    level_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="locked")
    score: Mapped[int] = mapped_column(Integer, default=0)
    time_used: Mapped[int] = mapped_column(Integer, default=0)
    hints_used: Mapped[list] = mapped_column(StringArray, default=list)
    energy_left: Mapped[int] = mapped_column(Integer, default=100)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    dimension_coverage: Mapped[dict] = mapped_column(JSONType, default=dict)
    badge: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HintUsage(UUIDPK, Base):
    """hint_usage{id,progress_id,level,ts}"""

    __tablename__ = "hint_usages"

    progress_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("level_progress.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(4), default="H1")
    energy_cost: Mapped[int] = mapped_column(Integer, default=10)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class Achievement(UUIDPK, Base):
    """achievement{id,name,condition,rarity}"""

    __tablename__ = "achievements"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    condition: Mapped[str] = mapped_column(String(512), default="")
    rarity: Mapped[str] = mapped_column(String(16), default="common")


class UserProfile(UUIDPK, Base):
    """user_profile{radar{},points,tier,badges[]}"""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID, unique=True, nullable=False, index=True)
    radar: Mapped[dict] = mapped_column(JSONType, default=dict)
    points: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[str] = mapped_column(String(16), default="bronze")
    badges: Mapped[list] = mapped_column(StringArray, default=list)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate="now()")


class Rank(UUIDPK, Base):
    """rank{user_id,points,tier}"""

    __tablename__ = "ranks"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID, unique=True, nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[str] = mapped_column(String(16), default="bronze")


class HardeningOption(UUIDPK, Base):
    """hardening_option{id,type(prompt/permission/guardrail),diff_preview,expected_effect,side_effects}"""

    __tablename__ = "hardening_options"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    level_id: Mapped[str] = mapped_column(String(16), default="")
    type: Mapped[str] = mapped_column(String(16), default="prompt")
    diff_preview: Mapped[dict] = mapped_column(JSONType, default=dict)
    expected_effect: Mapped[str] = mapped_column(String(512), default="")
    side_effects: Mapped[str] = mapped_column(String(512), default="")
    applied_by_default: Mapped[bool] = mapped_column(Boolean, default=False)