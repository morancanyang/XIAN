"""评分 / 基准库（PRD 3.6.5）。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import (
    GUID,
    UUIDPK,
    Base,
    JSONType,
    TenantMixin,
    timestamp_default,
)


class Score(TenantMixin, UUIDPK, Base):
    """score{id,subject_type(agent/version),sec_score,grade,dimension_scores{},category_asr{},percentile,computed_at}"""

    __tablename__ = "scores"

    subject_type: Mapped[str] = mapped_column(String(16), default="agent")
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    sec_score: Mapped[int] = mapped_column(Integer, default=0)
    grade: Mapped[str] = mapped_column(String(1), default="D")
    dimension_scores: Mapped[dict] = mapped_column(JSONType, default=dict)
    category_asr: Mapped[dict] = mapped_column(JSONType, default=dict)
    percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    segment: Mapped[str] = mapped_column(String(64), default="general")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)


class Benchmark(UUIDPK, Base):
    """benchmark{segment,sample_size,mean,p50,p90}"""

    __tablename__ = "benchmarks"

    segment: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    mean: Mapped[float] = mapped_column(Float, default=0.0)
    percentiles: Mapped[dict] = mapped_column(JSONType, default=dict)
    common_weak_points: Mapped[list] = mapped_column(JSONType, default=list)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default())


class TrendPoint(UUIDPK, Base):
    """trend_point{agent_id,version_id,sec_score,ts}"""

    __tablename__ = "trend_points"

    agent_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    version_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True)
    sec_score: Mapped[int] = mapped_column(Integer, default=0)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=timestamp_default(), index=True)