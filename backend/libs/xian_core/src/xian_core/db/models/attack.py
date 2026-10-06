"""攻击记录 / 判定 / 裁判流水 / 观测事件（PRD 3.3、3.4、3.6）。"""

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
    TenantMixin,
    timestamp_default,
)


class AttackRecord(TenantMixin, UUIDPK, Base):
    """attack_record：PG 存结论摘要，明细在 ClickHouse（技术方案 6.2）。"""

    __tablename__ = "attack_records"

    agent_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    agent_version_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    case_id: Mapped[str] = mapped_column(String(64), default="")
    category_code: Mapped[str] = mapped_column(String(16), default="", index=True)
    strategy: Mapped[str] = mapped_column(String(64), default="")
    mutation_ops: Mapped[list] = mapped_column(JSONType, default=list)
    turns: Mapped[int] = mapped_column(Integer, default=1)
    verdict: Mapped[str] = mapped_column(String(16), default="fail", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    rule_hits: Mapped[list] = mapped_column(JSONType, default=list)
    evidence: Mapped[list] = mapped_column(JSONType, default=list)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    trace_key: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)


class Verdict(UUIDPK, Base):
    """verdict{id,record_id,level(golden/classifier/llm),result,confidence,rule_hits[],evidence[],judge_model,ts}"""

    __tablename__ = "verdicts"

    record_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("attack_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(16), default="llm")
    result: Mapped[str] = mapped_column(String(16), default="fail")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    rule_hits: Mapped[list] = mapped_column(JSONType, default=list)
    evidence: Mapped[list] = mapped_column(JSONType, default=list)
    judge_model: Mapped[str] = mapped_column(String(128), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)


class JudgeCall(UUIDPK, Base):
    """judge_call{id,record_id,prompt_version,model,raw_output,parsed,ts}"""

    __tablename__ = "judge_calls"

    record_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("attack_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1")
    model: Mapped[str] = mapped_column(String(128), default="")
    raw_output: Mapped[str] = mapped_column(Text, default="")
    parsed: Mapped[dict] = mapped_column(JSONType, default=dict)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class JudgeHealth(UUIDPK, Base):
    """judge_health{date,golden_ratio,agreement_rate,sample_audit_rate}（AC-03 度量落点）。"""

    __tablename__ = "judge_health"

    day: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    golden_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    agreement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    sample_audit_rate: Mapped[float] = mapped_column(Float, default=0.0)
    total_records: Mapped[int] = mapped_column(Integer, default=0)


class TraceEvent(TenantMixin, UUIDPK, Base):
    """trace_event 的 PG 侧索引；明细主体在 ClickHouse（技术方案 6.1）。"""

    __tablename__ = "trace_events"

    subject_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(32), default="output", index=True)
    actor: Mapped[str] = mapped_column(String(16), default="aut")
    name: Mapped[str] = mapped_column(String(128), default="")
    canary_hit: Mapped[bool] = mapped_column(default=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)


class EgressLog(TenantMixin, UUIDPK, Base):
    """egress_log{id,instance_id,mapped_domain,body_hash,canary_hit,ts}（明细在 ClickHouse）。"""

    __tablename__ = "egress_logs"

    instance_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    mapped_domain: Mapped[str] = mapped_column(String(255), default="")
    body_hash: Mapped[str] = mapped_column(String(64), default="")
    canary_hit: Mapped[bool] = mapped_column(default=False, index=True)
    allowed: Mapped[bool] = mapped_column(default=True)
    detail: Mapped[dict] = mapped_column(JSONType, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)