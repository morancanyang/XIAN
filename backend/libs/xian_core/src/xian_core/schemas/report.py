"""评分 / 复盘 / 修复 / 报告契约（PRD 3.6.5 / 3.7 / 3.8）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from .common import Severity, StrictModel, Verdict


class DimensionScore(StrictModel):
    score: float
    weight: float
    sample_sufficient: bool = True
    categories: dict[str, float] = Field(default_factory=dict)


class ScoreOut(StrictModel):
    id: UUID
    subject_type: str
    subject_id: UUID
    sec_score: int
    grade: str
    dimension_scores: dict[str, DimensionScore]
    category_asr: dict[str, float]
    percentile: float | None = None
    segment: str = ""
    computed_at: datetime


class RootCauseOut(StrictModel):
    code: str
    name: str
    category: str
    fix_playbook_ref: str


class FindingOut(StrictModel):
    id: UUID
    campaign_id: UUID
    record_ids: list[UUID]
    root_cause_code: str
    severity: Severity
    affected_config: dict[str, Any]
    impact: str
    trace_refs: list[str]
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class RecommendationOut(StrictModel):
    id: UUID
    finding_id: UUID
    type: str
    priority: str
    effort: str
    diff_payload: dict[str, Any]
    playbook_ref: str
    expected_effect: str = ""
    side_effects: str = ""
    applied: bool = False


class RemediationRunOut(StrictModel):
    id: UUID
    recommendation_id: UUID
    applied_at: datetime
    before_sec_score: int
    after_sec_score: int
    before_asr: float
    after_asr: float
    regression_pass_rate: float
    status: str


class ReportOut(StrictModel):
    id: UUID
    subject_type: str
    subject_id: UUID
    version: int
    sec_score: int
    grade: str
    chapters: dict[str, Any]
    object_keys: dict[str, str]
    share: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ReportExportOut(StrictModel):
    id: UUID
    report_id: UUID
    format: str
    desensitize_level: str
    file_ref: str
    ts: datetime


class GateRuleIn(StrictModel):
    max_score_drop: int = 5
    block_on_severity: str = "high"
    enabled: bool = True


class GateRuleOut(GateRuleIn):
    id: UUID
    tenant_id: UUID


class ScanJobOut(StrictModel):
    id: UUID
    agent_id: UUID
    trigger: str
    status: str
    verdict: Verdict | None = None
    ci_context: dict[str, Any] = Field(default_factory=dict)
    pipeline_url: str = ""
    exit_code: int | None = None