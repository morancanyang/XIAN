"""个人中心：能力雷达 / 段位 / 徽章墙（PRD 3.4.4、3.4.5）。"""

from __future__ import annotations

from fastapi import APIRouter
from xian_core.db.repositories import LevelProgressRepository
from xian_core.levels import (
    LEVELS,
    achievement_catalog,
    award_badges,
    build_radar,
    tier_for,
)
from xian_core.schemas.level import AchievementOut, UserProfileOut

from ..deps import PrincipalDep, SessionDep

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=UserProfileOut)
async def my_profile(session: SessionDep, principal: PrincipalDep) -> UserProfileOut:
    """从关卡进度聚合雷达分、积分、段位与徽章。"""
    rows = await LevelProgressRepository(session, principal.tenant_id).for_user(principal.user_id)

    completed = [r.level_id for r in rows if r.status == "passed"]
    hints_by_level = {r.level_id: list(r.hints_used or []) for r in rows}
    coverage: dict[str, float] = {}
    for row in rows:
        for dim, value in (row.dimension_coverage or {}).items():
            coverage[dim] = max(coverage.get(dim, 0.0), float(value))
    for code in completed:
        level = next((lv for lv in LEVELS if lv["code"] == code), None)
        for technique in (level or {}).get("techniques", []):
            coverage.setdefault(technique, 0.0)
            coverage[technique] = max(coverage[technique], 0.8)

    points = sum(int(r.score or 0) for r in rows)
    return UserProfileOut(
        user_id=principal.user_id,
        radar=build_radar(coverage),
        points=points,
        tier=tier_for(points),
        badges=award_badges(completed=completed, hints_by_level=hints_by_level),
    )


@router.get("/achievements", response_model=list[AchievementOut])
async def achievements(_session: SessionDep, _principal: PrincipalDep) -> list[AchievementOut]:
    return [AchievementOut(**a) for a in achievement_catalog()]