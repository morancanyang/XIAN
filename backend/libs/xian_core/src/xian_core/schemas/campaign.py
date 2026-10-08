"""战役 / 战役计划 / 战役运行态契约（PRD 3.3）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from .common import (
    CampaignStatus,
    Intensity,
    JudgeMode,
    OutputMode,
    StrictModel,
)


class Budget(StrictModel):
    token: int = 200_000
    cases: int = 60
    minutes: int = 30


class CampaignCreate(StrictModel):
    agent_id: UUID
    scenario_id: UUID | None = None
    agent_version_id: UUID | None = None
    scope: list[str] = Field(default_factory=list, description="勾选的攻击类别 XM-xx")
    intensity: Intensity = Intensity.standard
    budget: Budget = Field(default_factory=Budget)
    constraints: dict[str, Any] = Field(default_factory=dict)
    judge_mode: JudgeMode = JudgeMode.standard
    output_mode: OutputMode = OutputMode.summary
    preset_id: str = "standard"


class CampaignUpdate(StrictModel):
    scope: list[str] | None = None
    intensity: Intensity | None = None
    budget: Budget | None = None
    constraints: dict[str, Any] | None = None
    judge_mode: JudgeMode | None = None
    output_mode: OutputMode | None = None
    status: CampaignStatus | None = None


class PlanPreviewIn(StrictModel):
    """创建前预览计划入参：与 CampaignCreate 的作战字段保持一致。"""

    agent_id: UUID | None = None
    scope: list[str] = Field(default_factory=list, description="勾选的攻击类别 XM-xx")
    intensity: Intensity = Intensity.standard
    budget: Budget = Field(default_factory=Budget)


class Estimate(StrictModel):
    """3.3.4.8.1 预算估算器。"""

    token: int
    minutes: int
    cases: int


class DagNode(StrictModel):
    id: str
    category_code: str
    stage: str
    case_ids: list[str] = Field(default_factory=list)
    budget_split: dict[str, int] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    weight: float = 1.0


class CampaignPlan(StrictModel):
    dag_nodes: list[DagNode] = Field(default_factory=list)
    edges: list[list[str]] = Field(default_factory=list)
    budget_split: dict[str, dict[str, int]] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)


class CampaignRunOut(StrictModel):
    id: UUID
    campaign_id: UUID
    status: str
    progress: int
    asr_live: float
    tokens_used: int
    budget_left: int
    started_at: datetime | None = None
    ended_at: datetime | None = None


class CampaignOut(StrictModel):
    id: UUID
    tenant_id: UUID
    agent_id: UUID
    agent_version_id: UUID | None = None
    scenario_instance_id: UUID | None = None
    scope: list[str]
    intensity: Intensity
    budget: dict[str, Any]
    constraints: dict[str, Any]
    judge_mode: JudgeMode
    output_mode: OutputMode
    preset_id: str
    status: CampaignStatus
    sec_score: int | None = None
    grade: str | None = None
    plan_dag: dict[str, Any] = Field(default_factory=dict)
    progress: int = 0
    created_by: UUID | None = None
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None

    @model_validator(mode="after")
    def _backfill_grade(self) -> CampaignOut:
        """等级按 SecScore 回推，兼容早期只落了分、没落等级的历史战役。"""
        if self.grade is None and self.sec_score is not None:
            from ..scoring.secscore import grade_of
            self.grade = grade_of(int(self.sec_score))
        return self


class MutationOpSpec(StrictModel):
    """mutation_op{id,name,type,semantics_safe,success_rate}"""

    name: str
    type: str = "lexical"
    semantics_safe: bool = True
    success_rate: float = 0.0
    description: str = ""

class PresetOut(StrictModel):
    id: str
    name: str
    scope: list[str]
    intensity: Intensity
    budget_default: Budget