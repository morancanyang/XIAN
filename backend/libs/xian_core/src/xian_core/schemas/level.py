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
    # 本次提交的判定。已通关的关卡重复提交时 status 仍是 passed，少了这两个字段，
    # 前端只能拿历史状态弹"通关成功"——空提交也能刷分。
    attempt_passed: bool = False
    attempt_reason: str = ""


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
    # 段位阶梯由后端 TIERS 统一算：前端不再各自硬编码阈值，
    # 之前写死 2000（钻石档），gold 用户会看到"再获得 1010 积分晋级"这种跳档文案。
    next_tier: str | None = None
    points_to_next_tier: int = 0
    tier_progress: float = 0.0
    badges: list[str]


class AchievementOut(StrictModel):
    id: str
    name: str
    condition: str
    rarity: str