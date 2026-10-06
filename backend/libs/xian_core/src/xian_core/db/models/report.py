"""报告 / 导出 / 订阅 / 通知 / 告警 / 门禁 / 巡检（PRD 3.8）。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
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


class Report(TenantMixin, UUIDPK, Base):
    """report{id,subject_type,subject_id,version,sec_score,grade,chapters[],object_keys[],share{},created_at}"""

    __tablename__ = "reports"

    subject_type: Mapped[str] = mapped_column(String(16), default="campaign")
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    sec_score: Mapped[int] = mapped_column(Integer, default=0)
    grade: Mapped[str] = mapped_column(String(1), default="D")
    chapters: Mapped[dict] = mapped_column(JSONType, default=dict)
    object_keys: Mapped[dict] = mapped_column(JSONType, default=dict)
    share: Mapped[dict] = mapped_column(JSONType, default=dict)
    partial: Mapped[bool] = mapped_column(default=False)
    coverage_pct: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)


class ReportExport(UUIDPK, Base):
    """report_export{id,report_id,format,desensitize_level,file_ref,ts}"""

    __tablename__ = "report_exports"

    report_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    format: Mapped[str] = mapped_column(String(16), default="html")
    desensitize_level: Mapped[str] = mapped_column(String(16), default="standard")
    file_ref: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(16), default="done")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class Subscription(UUIDPK, Base):
    """subscription{id,user_id,cadence,channels[],recipients[]}"""

    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    cadence: Mapped[str] = mapped_column(String(16), default="weekly")
    channels: Mapped[list] = mapped_column(StringArray, default=list)
    recipients: Mapped[list] = mapped_column(StringArray, default=list)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class Notification(UUIDPK, Base):
    """notification{id,type,channel,payload,ts}"""

    __tablename__ = "notifications"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(32), default="system")
    channel: Mapped[str] = mapped_column(String(16), default="inapp")
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    retries: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)


class Alert(TenantMixin, UUIDPK, Base):
    """alert{id,campaign_id,record_id,severity,channels[],status}"""

    __tablename__ = "alerts"

    campaign_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    record_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="high")
    channels: Mapped[list] = mapped_column(StringArray, default=list)
    status: Mapped[str] = mapped_column(String(16), default="open")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)


class GateRule(TenantMixin, UUIDPK, Base):
    """gate_rule{id,tenant_id,max_score_drop,block_on_severity,enabled}"""

    __tablename__ = "gate_rules"

    max_score_drop: Mapped[int] = mapped_column(Integer, default=5)
    block_on_severity: Mapped[str] = mapped_column(String(16), default="high")
    enabled: Mapped[bool] = mapped_column(default=True)
    webhook_url: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class ScanJob(TenantMixin, UUIDPK, Base):
    """scan_job{id,agent_id,trigger(ci/schedule/manual),status,verdict,ci_context,pipeline_url,exit_code}"""

    __tablename__ = "scan_jobs"

    agent_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    agent_version_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    trigger: Mapped[str] = mapped_column(String(16), default="manual")
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ci_context: Mapped[dict] = mapped_column(JSONType, default=dict)
    pipeline_url: Mapped[str] = mapped_column(String(512), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)