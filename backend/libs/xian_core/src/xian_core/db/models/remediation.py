"""根因库 / Playbook / 发现 / 攻击路径 / 修复建议 / 复测（PRD 3.7）。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
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


class RootCause(UUIDPK, Base):
    """root_cause{id,name,category,fix_playbook_ref}（八大根因）。"""

    __tablename__ = "root_causes"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="")
    fix_playbook_ref: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    match_signals: Mapped[list] = mapped_column(JSONType, default=list)


class Playbook(UUIDPK, Base):
    """playbook{id,root_cause_id,artifacts[],min_version}"""

    __tablename__ = "playbooks"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    root_cause_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    artifacts: Mapped[list] = mapped_column(JSONType, default=list)
    min_version: Mapped[str] = mapped_column(String(16), default="1.0")
    expected_effect: Mapped[str] = mapped_column(String(512), default="")
    side_effects: Mapped[str] = mapped_column(String(512), default="")


class Finding(TenantMixin, UUIDPK, Base):
    """finding{id,campaign_id,root_cause_code,severity,affected_config,impact,trace_refs[]}"""

    __tablename__ = "findings"

    campaign_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    record_ids: Mapped[list] = mapped_column(StringArray, default=list)
    root_cause_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    affected_config: Mapped[dict] = mapped_column(JSONType, default=dict)
    impact: Mapped[str] = mapped_column(Text, default="")
    trace_refs: Mapped[list] = mapped_column(StringArray, default=list)
    evidence: Mapped[list] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class AttackPath(UUIDPK, Base):
    """attack_path{id,campaign_id/session_id,nodes[],edges[]}"""

    __tablename__ = "attack_paths"

    campaign_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    nodes: Mapped[list] = mapped_column(JSONType, default=list)
    edges: Mapped[list] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class Recommendation(UUIDPK, Base):
    """recommendation{id,finding_id,type,priority,effort,diff_payload,playbook_ref}"""

    __tablename__ = "recommendations"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(32), default="prompt")
    priority: Mapped[str] = mapped_column(String(4), default="P1")
    effort: Mapped[str] = mapped_column(String(16), default="M")
    diff_payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    playbook_ref: Mapped[str] = mapped_column(String(64), default="")
    expected_effect: Mapped[str] = mapped_column(String(512), default="")
    side_effects: Mapped[str] = mapped_column(String(512), default="")
    applied: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class RemediationRun(UUIDPK, Base):
    """remediation_run{id,recommendation_id,applied_at,before,after,regression_pass_rate,status}"""

    __tablename__ = "remediation_runs"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    before_sec_score: Mapped[int] = mapped_column(Integer, default=0)
    after_sec_score: Mapped[int] = mapped_column(Integer, default=0)
    before_asr: Mapped[float] = mapped_column(Float, default=0.0)
    after_asr: Mapped[float] = mapped_column(Float, default=0.0)
    regression_pass_rate: Mapped[float] = mapped_column(Float, default=0.0)
    replayed_record_ids: Mapped[list] = mapped_column(StringArray, default=list)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    reverted: Mapped[bool] = mapped_column(default=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)