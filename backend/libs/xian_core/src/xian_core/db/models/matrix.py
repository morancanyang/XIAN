"""攻击矩阵 / 用例库 / 贡献评审（PRD 3.5）。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

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


class AttackCategory(TenantMixin, UUIDPK, Base):
    """attack_category{id,code,name,stage,attack_surface,difficulty,impact,techniques[],detection_signals[],owasp_ref,atlas_ref}"""

    __tablename__ = "attack_categories"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), default="")
    attack_surface: Mapped[str] = mapped_column(String(64), default="")
    difficulty: Mapped[str] = mapped_column(String(16), default="medium")
    impact: Mapped[str] = mapped_column(String(16), default="high")
    techniques: Mapped[list] = mapped_column(StringArray, default=list)
    detection_signals: Mapped[list] = mapped_column(StringArray, default=list)
    owasp_ref: Mapped[list] = mapped_column(StringArray, default=list)
    atlas_ref: Mapped[list] = mapped_column(StringArray, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(default=True)


class FrameworkMapping(UUIDPK, Base):
    """framework_mapping{framework,clause,category_ids[],coverage}"""

    __tablename__ = "framework_mappings"

    framework: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    clause: Mapped[str] = mapped_column(String(128), nullable=False)
    category_ids: Mapped[list] = mapped_column(StringArray, default=list)
    coverage: Mapped[str] = mapped_column(String(32), default="covered")
    note: Mapped[str] = mapped_column(String(255), default="")


class AttackCase(UUIDPK, TenantMixin, TimestampMixin, Base):
    """attack_case{id,category_id,title,payload_template,variables[],scenario_tags[],success_criteria,judge_prompt,severity,status,version,contributor,success_rate}"""

    __tablename__ = "attack_cases"

    case_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    category_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_template: Mapped[str] = mapped_column(Text, default="")
    variables: Mapped[list] = mapped_column(StringArray, default=list)
    scenario_tags: Mapped[list] = mapped_column(StringArray, default=list)
    difficulty: Mapped[str] = mapped_column(String(16), default="medium")
    success_criteria: Mapped[dict] = mapped_column(JSONType, default=dict)
    judge_prompt: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default="high")
    status: Mapped[str] = mapped_column(String(16), default="published", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    contributor: Mapped[str] = mapped_column(String(128), default="platform")
    success_rate: Mapped[float] = mapped_column(default=0.0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    export_allowed: Mapped[bool] = mapped_column(default=False)


class CaseReview(UUIDPK, Base):
    """case_review{id,case_id,reviewer,result,comment,ts}"""

    __tablename__ = "case_reviews"

    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reviewer: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True)
    result: Mapped[str] = mapped_column(String(16), default="pending")
    comment: Mapped[str] = mapped_column(Text, default="")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class Contribution(UUIDPK, Base):
    """contribution{id,author,case_id,pipeline_status,points}"""

    __tablename__ = "contributions"

    author: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    case_id: Mapped[str] = mapped_column(String(64), default="")
    pipeline_status: Mapped[str] = mapped_column(String(32), default="submitted")
    points: Mapped[int] = mapped_column(Integer, default=0)
    auto_test_result: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())