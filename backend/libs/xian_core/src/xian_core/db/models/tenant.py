"""租户 / 用户 / 成员 / 配额（PRD 3.9）。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import (
    GUID,
    UUIDPK,
    Base,
    JSONType,
    TenantMixin,
    TimestampMixin,
    timestamp_default,
)


class Tenant(UUIDPK, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="free")
    quota: Mapped[dict] = mapped_column(JSONType, default=dict)

    members: Mapped[list[Member]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class User(UUIDPK, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="active")


class Member(UUIDPK, TimestampMixin, Base):
    """member{user_id,tenant_id,role,status}"""

    __tablename__ = "members"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_member_tenant_user"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), default="blue")
    status: Mapped[str] = mapped_column(String(32), default="active")

    tenant: Mapped[Tenant] = relationship(back_populates="members")


class TenantFeature(UUIDPK, Base):
    """tenant_feature{tenant_id,flag,rollout}（技术方案 7.7 特性开关）。"""

    __tablename__ = "tenant_features"
    __table_args__ = (UniqueConstraint("tenant_id", "flag", name="uq_tenant_feature"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("tenants.id"), nullable=False, index=True)
    flag: Mapped[str] = mapped_column(String(64), nullable=False)
    rollout: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class QuotaUsage(TenantMixin, UUIDPK, Base):
    """quota_usage{tenant_id,metric,used,window}"""

    __tablename__ = "quota_usages"

    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    used: Mapped[int] = mapped_column(Integer, default=0)
    window: Mapped[str] = mapped_column(String(32), default="daily")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate="now()")


class AuditLog(UUIDPK, Base):
    """audit_log{id,tenant_id,user_id,action,target,result,ip,ts}（追加式，不可更新）。"""

    __tablename__ = "audit_logs"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(GUID, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(GUID, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(255), default="")
    result: Mapped[str] = mapped_column(String(32), default="success")
    ip: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[dict] = mapped_column(JSONType, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)


class AbuseEvent(TenantMixin, UUIDPK, Base):
    """abuse_event{id,tenant_id,type,severity,evidence[],status}"""

    __tablename__ = "abuse_events"

    type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    evidence: Mapped[list] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(16), default="open")
    handled_by: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())