"""个人中心：能力雷达 / 段位 / 徽章墙（PRD 3.4.4、3.4.5）。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from fastapi import APIRouter
from xian_core.db.repositories import LevelProgressRepository
from xian_core.levels import (
    LEVELS,
    achievement_catalog,
    award_badges,
    build_radar,
    next_tier_for,
    tier_for,
    tier_progress,
)
from xian_core.schemas.level import AchievementOut, UserProfileOut

from ..deps import PrincipalDep, SessionDep

router = APIRouter(prefix="/profile", tags=["profile"])


def _coverage(rows: Iterable[Any]) -> dict[str, float]:
    """按关卡进度聚合法手覆盖度（PRD 3.4.4）。

    有 dimension_coverage 的行以提交时记录的为准——那是用户实际用过的手法按得分算出来的。
    只在通关过但没有覆盖度的历史行上做兜底：按该关得分给一个下限估计，而不是给每个手法
    打固定的 0.8。早期版本压根不写覆盖度，兜底又是常量，结果雷达六个轴恒为 80。
    """
    techniques_by_level = {str(lv["code"]): list(lv.get("techniques") or []) for lv in LEVELS}
    coverage: dict[str, float] = {}
    for row in rows:
        recorded = row.dimension_coverage or {}
        if recorded:
            for name, value in recorded.items():
                coverage[str(name)] = max(coverage.get(str(name), 0.0), float(value))
            continue
        if row.status != "passed":
            continue
        estimate = max(0.8, min(1.0, float(row.score or 0) / 100.0))
        for technique in techniques_by_level.get(str(row.level_id), []):
            coverage[technique] = max(coverage.get(technique, 0.0), estimate)
    return coverage


@router.get("", response_model=UserProfileOut)
async def my_profile(session: SessionDep, principal: PrincipalDep) -> UserProfileOut:
    """从关卡进度聚合雷达分、积分、段位与徽章。"""
    rows = await LevelProgressRepository(session, principal.tenant_id).for_user(principal.user_id)

    completed = [r.level_id for r in rows if r.status == "passed"]
    hints_by_level = {r.level_id: list(r.hints_used or []) for r in rows}
    points = sum(int(r.score or 0) for r in rows)
    next_tier, to_next = next_tier_for(points)
    return UserProfileOut(
        user_id=principal.user_id,
        radar=build_radar(_coverage(rows)),
        points=points,
        tier=tier_for(points),
        next_tier=next_tier,
        points_to_next_tier=to_next,
        tier_progress=tier_progress(points),
        badges=award_badges(completed=completed, hints_by_level=hints_by_level),
    )


@router.get("/achievements", response_model=list[AchievementOut])
async def achievements(_session: SessionDep, _principal: PrincipalDep) -> list[AchievementOut]:
    # ACHIEVEMENTS 内容资产里字段名是 code，对外契约 AchievementOut 用的是 id，显式映射。
    return [
        AchievementOut(id=a["code"], name=a["name"], condition=a["condition"], rarity=a["rarity"])
        for a in achievement_catalog()
    ]
