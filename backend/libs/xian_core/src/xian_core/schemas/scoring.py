"""评分输入输出与基准库契约（PRD 3.6.5）。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from .common import StrictModel, Verdict


class ScoreInput(StrictModel):
    """评分引擎输入：一次战役/会话的判定结果集合。"""

    subject_type: str
    subject_id: UUID
    segment: str = "general"
    category_results: dict[str, list[Verdict]] = Field(default_factory=dict)
    category_weights: dict[str, float] = Field(default_factory=dict)


class BenchmarkOut(StrictModel):
    segment: str
    sample_size: int
    mean: float
    percentiles: dict[str, float]


class TrendPointOut(StrictModel):
    agent_id: UUID
    version_id: UUID
    sec_score: int
    ts: datetime