"""靶场场景 / 实例 / 蜜标契约（PRD 3.1）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from .common import Difficulty, StrictModel, ToolScope

CANARY_NAMESPACE = "sk-canary"


class ScenarioTool(StrictModel):
    name: str
    scope: ToolScope
    risk_level: str = "low"
    require_confirm: bool = False
    description: str = ""


class ScenarioCanary(StrictModel):
    id: UUID | None = None
    type: str = Field(description="key / phone / id / order")
    value: str
    plant_location: list[str] = Field(default_factory=list)
    status: str = "planted"

    @model_validator(mode="after")
    def _must_be_fake(self) -> ScenarioCanary:
        """假凭证必须落在保留命名空间内，防止真实凭证混入（PRD 3.1.5.6）。"""
        if self.type == "key" and not self.value.startswith(CANARY_NAMESPACE) and "{{" not in self.value:
            raise ValueError(f"密钥类蜜标必须使用保留命名空间 {CANARY_NAMESPACE}- 开头")
        if not self.value:
            raise ValueError("蜜标值不能为空")
        return self

class ScenarioDsl(StrictModel):
    """场景 DSL 种子格式（技术方案 7.3）。"""

    id: str = Field(pattern=r"^S\d+$")
    name: str
    difficulty: Difficulty = Difficulty.beginner
    category: str = "general"
    agent_form: str = ""
    exam_tags: list[str] = Field(default_factory=list)
    description: str = ""
    env: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)
    tools: list[ScenarioTool] = Field(default_factory=list)
    canaries: list[ScenarioCanary] = Field(default_factory=list)
    monitors: list[str] = Field(default_factory=list)
    script: list[str] = Field(default_factory=list)
    baseline_tasks: int = 3
    status: str = "published"


class ScenarioOut(StrictModel):
    id: UUID
    code: str
    name: str
    category: str
    difficulty: Difficulty
    env_template: dict[str, Any]
    script: list[str]
    default_difficulty: str
    tools: list[ScenarioTool]
    canary_types: list[str]
    monitors: list[str]
    status: str


class InstanceCreate(StrictModel):
    scenario_id: UUID
    data_scale: int = Field(default=200, ge=1, le=10000)
    language: str = "zh-CN"
    canary_enhanced: bool = True
    run_baseline: bool = True


class ScenarioInstanceOut(StrictModel):
    id: UUID
    scenario_id: UUID
    tenant_id: UUID
    seed_data_snapshot: dict[str, Any]
    status: str
    created_at: datetime
    expired_at: datetime | None = None


class CanaryHitOut(StrictModel):
    id: UUID
    canary_id: UUID
    via: str
    trace_ref: str
    ts: datetime


class BaselineTaskOut(StrictModel):
    name: str
    passed: bool
    detail: str = ""