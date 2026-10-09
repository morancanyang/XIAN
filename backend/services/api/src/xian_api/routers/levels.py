"""十关教学关卡（PRD 3.4.5）。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from xian_core.db.models import Level, LevelProgress
from xian_core.db.repositories import LevelProgressRepository, LevelRepository
from xian_core.levels import (
    HINT_COST,
    LEVELS,
    TOTAL_ENERGY,
    LevelContext,
    consume_hint,
    evaluate,
    is_unlocked,
    merge_coverage,
    options_for,
    score_attempt,
)
from xian_core.schemas.level import HintOut, HintUseIn, LevelOut, LevelProgressOut

from ..deps import PrincipalDep, SessionDep

router = APIRouter(prefix="/levels", tags=["levels"])


def to_level_out(row: Level) -> LevelOut:
    """Level 主键为 UUID，业务主键是 code：对外以 code 作为稳定标识。"""
    return LevelOut(
        id=row.code,
        name=row.name,
        scenario_code=row.scenario_code,
        goal=row.goal,
        pass_criteria=dict(row.pass_criteria or {}),
        techniques=list(row.techniques or []),
        hints={"H1": row.h1, "H2": row.h2, "H3": row.h3},
        unlock_rule=row.unlock_rule,
        difficulty=row.difficulty,
    )


@router.get("", response_model=list[LevelOut])
async def list_levels(session: SessionDep, principal: PrincipalDep) -> list[LevelOut]:
    repo = LevelRepository(session, principal.tenant_id)
    rows = await repo.all_ordered()
    if not rows:
        for meta in LEVELS:
            await repo.add(
                Level(
                    tenant_id=principal.tenant_id,
                    code=meta["code"],
                    name=meta["name"],
                    scenario_code=meta["scenario_code"],
                    goal=meta["goal"],
                    pass_criteria=meta["pass_criteria"],
                    techniques=list(meta["techniques"]),
                    h1=meta["h1"],
                    h2=meta["h2"],
                    h3=meta["h3"],
                    unlock_rule=meta["unlock_rule"],
                    difficulty=meta["difficulty"],
                    order_idx=meta["order_idx"],
                    status=meta["status"],
                )
            )
        await session.commit()
        rows = await repo.all_ordered()
    return [to_level_out(r) for r in rows]


@router.get("/progress", response_model=list[LevelProgressOut])
async def my_progress(session: SessionDep, principal: PrincipalDep) -> list[LevelProgressOut]:
    rows = await LevelProgressRepository(session, principal.tenant_id).for_user(principal.user_id)
    return [LevelProgressOut.model_validate(r) for r in rows]


@router.post("/{code}/start", response_model=LevelProgressOut, status_code=status.HTTP_201_CREATED)
async def start_level(code: str, session: SessionDep, principal: PrincipalDep) -> LevelProgressOut:
    repo = LevelProgressRepository(session, principal.tenant_id)
    existing = await repo.get_for_user_level(principal.user_id, code)
    if existing is not None:
        return LevelProgressOut.model_validate(existing)
    done = [r.level_id for r in await repo.for_user(principal.user_id) if r.status == "passed"]
    row = await repo.add(
        LevelProgress(
            user_id=principal.user_id, level_id=code, status="unlocked" if is_unlocked(code, done) else "locked",
            energy_left=TOTAL_ENERGY,
        )
    )
    await session.commit()
    await session.refresh(row)
    return LevelProgressOut.model_validate(row)


@router.post("/{code}/hint", response_model=HintOut)
async def use_hint(code: str, payload: HintUseIn, session: SessionDep, principal: PrincipalDep) -> HintOut:
    """三级提示：H1 方向 / H2 思路 / H3 近似 payload，分别扣 10/20/40 能量。"""
    repo = LevelProgressRepository(session, principal.tenant_id)
    row = await repo.get_for_user_level(principal.user_id, code)
    if row is None:
        row = await repo.add(LevelProgress(user_id=principal.user_id, level_id=code, status="unlocked",
                                          energy_left=TOTAL_ENERGY))
    level = await LevelRepository(session, principal.tenant_id).by_code(code)
    if level is None:
        raise HTTPException(404, f"关卡 {code} 不存在")
    progress = type("P", (), {"hints_used": list(row.hints_used), "energy_left": row.energy_left})()
    ok, message = consume_hint(progress, payload.hint_level)
    if not ok:
        raise HTTPException(409, message)
    row.hints_used = list(progress.hints_used)
    row.energy_left = progress.energy_left
    await session.commit()
    text = getattr(level, payload.hint_level.lower(), "")
    return HintOut(
        level=payload.hint_level,
        energy_cost=HINT_COST[payload.hint_level],
        content=str(text),
        energy_left=row.energy_left,
    )


@router.post("/{code}/submit", response_model=LevelProgressOut)
async def submit_attempt(code: str, body: dict, session: SessionDep, principal: PrincipalDep) -> LevelProgressOut:
    """提交一次尝试，按 PRD 3.4.5.1 可量化条件判定通关。"""
    repo = LevelProgressRepository(session, principal.tenant_id)
    row = await repo.get_for_user_level(principal.user_id, code)
    if row is None:
        raise HTTPException(404, "请先开始关卡")
    level = await LevelRepository(session, principal.tenant_id).by_code(code)
    if level is None:
        raise HTTPException(404, f"关卡 {code} 不存在")
    ctx = LevelContext(
        output=str(body.get("output", "")),
        tool_calls=list(body.get("tool_calls", [])),
        egress_bodies=list(body.get("egress_bodies", [])),
        system_prompt=str(body.get("system_prompt", "")),
        secret_fields=dict(body.get("secret_fields", {})),
        secret_token=str(body.get("secret_token", "")),
        canary_values=list(body.get("canary_values", [])),
        turns=list(body.get("turns", [])),
        tokens_used=int(body.get("tokens_used", 0)),
        baseline_tokens=int(body.get("baseline_tokens", 0)),
        memory_after_new_session=str(body.get("memory_after_new_session", "")),
    )
    verdict = evaluate(level.pass_criteria, ctx)
    row.attempts = (row.attempts or 0) + 1
    row.time_used = int(body.get("time_used", 0))
    if verdict.passed:
        technique = str(body.get("technique", level.techniques[0] if level.techniques else ""))
        score = score_attempt(
            passed=True,
            hints_used=list(row.hints_used),
            technique=technique,
            seen_techniques=list(body.get("seen_techniques", [])),
        )
        row.status = "passed"
        row.score = max(row.score or 0, score)
        row.completed_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
        # 能力雷达的数据来源：只写这里一次。此前 dimension_coverage 永远是 {}，
        # profile 只能靠"通关过"给每个手法打 0.8，雷达六个轴恒为 80，跟账号表现无关。
        row.dimension_coverage = merge_coverage(
            existing=row.dimension_coverage,
            level_techniques=list(level.techniques or []),
            used=technique,
            quality=row.score / 100,
        )
    await session.commit()
    await session.refresh(row)
    out = LevelProgressOut.model_validate(row)
    # 回传本次判定：已通关的关卡重复提交时 row.status 一直是 passed，
    # 只回传历史状态会让空提交也弹"通关成功"。
    out.attempt_passed = verdict.passed
    out.attempt_reason = verdict.reason
    return out


@router.get("/{code}/hardening")
async def hardening(code: str, session: SessionDep, principal: PrincipalDep) -> list[dict[str, Any]]:
    return options_for(code)