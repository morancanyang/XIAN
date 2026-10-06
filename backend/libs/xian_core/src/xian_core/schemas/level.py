"""关卡教案 / 进度 / 徽章契约（PRD 3.4.5）。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field

from .common import Difficulty, StrictModel


class LevelOut(StrictModel):
    id: str
    name: str
    scenario_code: str
    goal: str
    pass_criteria: dict[str, Any]
    techniques: list[str]
    hints: dict[str, str]
    unlock_rule: str
    difficulty: Difficulty = Difficulty.easy


class LevelProgressOut(StrictModel):
    id: UUID
    user_id: UUID
    level_id: str
    status: str
    score: int
    time_used: int
    hints_used: list[str]
    energy_left: int
    dimension_coverage: dict[str, float]
    badge: str | None = None


class HintUseIn(StrictModel):
    hint_level: str = Field(pattern="^H[123]$")


class HintOut(StrictModel):
    level: str
    content: str
    energy_cost: int
    energy_left: int


class UserProfileOut(StrictModel):
    user_id: UUID
    radar: dict[str, float]
    points: int
    tier: str
    badges: list[str]


class AchievementOut(StrictModel):
    id: str
    name: str
    condition: str
    rarity: str