"""十关教学关卡、三级提示、能量、徽章与段位（PRD 3.4.5）。"""

from .evaluator import LevelContext, Verdict, evaluate
from .fixtures import ACHIEVEMENTS, HINT_COST, LEVELS, TIERS, TOTAL_ENERGY
from .hardening import OPTIONS, default_applied, options_for
from .progress import (
    RADAR_DIMENSIONS,
    Progress,
    TECHNIQUE_DIMENSION,
    achievement_catalog,
    award_badges,
    build_radar,
    consume_hint,
    is_unlocked,
    new_progress,
    next_recommended,
    score_attempt,
    tier_for,
    unlocked_levels,
)

__all__ = [
    "ACHIEVEMENTS",
    "RADAR_DIMENSIONS",
    "HINT_COST",
    "LEVELS",
    "OPTIONS",
    "TECHNIQUE_DIMENSION",
    "TIERS",
    "TOTAL_ENERGY",
    "LevelContext",
    "Progress",
    "Verdict",
    "achievement_catalog",
    "award_badges",
    "build_radar",
    "consume_hint",
    "default_applied",
    "evaluate",
    "is_unlocked",
    "new_progress",
    "next_recommended",
    "options_for",
    "score_attempt",
    "tier_for",
    "unlocked_levels",
]