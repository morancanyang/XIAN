"""模式一：战术后台（战役编排、计划、WS 事件）（PRD 3.3.4）。"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from xian_core.db.models import Campaign
from xian_core.db.repositories import (
    AgentRepository,
    AttackRecordRepository,
    CampaignRepository,
    ScenarioInstanceRepository,
)
from xian_core.redteam import AgentSurface, HistorySignal, build_plan
from xian_core.schemas.campaign import (
    Budget,
    CampaignCreate,
    CampaignOut,
    CampaignPlan,
    CampaignUpdate,
    PlanPreviewIn,
)
from xian_core.schemas.common import Intensity, enum_str

from ..deps import Principal, PrincipalDep, SessionDep, require

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

# 战役状态机（PRD 2.2.4）
CAMPAIGN_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"scheduled", "cancelled"},
    "scheduled": {"preparing", "cancelled"},
    "preparing": {"attacking", "env_failed"},
    "attacking": {"analyzing", "tripped", "cancelled"},
    "analyzing": {"reporting"},
    "reporting": {"completed", "cancelled"},
    "tripped": {"reporting"},
    "completed": set(),
    "cancelled": set(),
    "env_failed": set(),
}


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate, session: SessionDep, principal: Annotated[Principal, Depends(require("campaign:run"))]
) -> CampaignOut:
    repo = CampaignRepository(session, principal.tenant_id)
    agent_repo = AgentRepository(session, principal.tenant_id)
    agents = await agent_repo.list_by_id(payload.agent_id)
    if not agents:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent 不存在或无权访问")
    agent = agents[0]
    if not agent.ownership_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Agent 归属校验未通过，不能作为模式一目标（AC-09）")
    if payload.scenario_id:
        instances = await ScenarioInstanceRepository(session, principal.tenant_id).list_by_id(payload.scenario_id)
        if not instances:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "场景实例不存在或无权访问")
    row = await repo.add(
        Campaign(
            tenant_id=principal.tenant_id,
            agent_id=payload.agent_id,
            agent_version_id=payload.agent_version_id,
            scenario_instance_id=payload.scenario_id,
            intensity=enum_str(payload.intensity),
            scope=list(payload.scope),
            budget=payload.budget.model_dump(),
            constraints=dict(payload.constraints),
            judge_mode=enum_str(payload.judge_mode),
            output_mode=enum_str(payload.output_mode),
            preset_id=payload.preset_id,
            status="draft",
            created_by=principal.user_id,
        )
    )
    await session.commit()
    await session.refresh(row)
    return CampaignOut.model_validate(row)


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(session: SessionDep, principal: PrincipalDep) -> list[CampaignOut]:
    rows = await CampaignRepository(session, principal.tenant_id).list()
    return [CampaignOut.model_validate(r) for r in rows]


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> CampaignOut:
    row = await CampaignRepository(session, principal.tenant_id).get_optional(campaign_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "战役不存在")
    return CampaignOut.model_validate(row)


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: uuid.UUID, payload: CampaignUpdate, session: SessionDep,
    principal: Annotated[Principal, Depends(require("campaign:run"))],
) -> CampaignOut:
    repo = CampaignRepository(session, principal.tenant_id)
    row = await repo.get_optional(campaign_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "战役不存在")
    fields = payload.model_dump(exclude_unset=True)
    if "status" in fields and fields["status"] is not None:
        target = fields["status"].value if hasattr(fields["status"], "value") else fields["status"]
        if target not in CAMPAIGN_TRANSITIONS.get(row.status, set()):
            raise HTTPException(status.HTTP_409_CONFLICT, f"战役状态不允许从 {row.status} 迁移到 {target}")
        fields["status"] = target
    for key, value in fields.items():
        setattr(row, key, value)
    await session.commit()
    await session.refresh(row)
    return CampaignOut.model_validate(row)


@router.post("/preview-plan", response_model=CampaignPlan)
async def preview_campaign_plan(
    payload: PlanPreviewIn, session: SessionDep, principal: PrincipalDep
) -> CampaignPlan:
    """创建前预览战役计划：与正式计划同一套指挥官规则，但不落库（PRD 3.3.5.8.1）。"""
    agent_id = payload.agent_id or uuid.UUID(int=0)
    if payload.agent_id is not None:
        agent = await AgentRepository(session, principal.tenant_id).get_optional(agent_id)
        if agent is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent 不存在或无权访问")
    mirror = Campaign(
        tenant_id=principal.tenant_id,
        agent_id=agent_id,
        scope=list(payload.scope),
        intensity=enum_str(payload.intensity),
        budget=payload.budget.model_dump(),
        status="draft",
    )
    return await build_campaign_plan(mirror, principal.tenant_id, session)


@router.post("/{campaign_id}/plan", response_model=CampaignPlan)
async def plan_campaign(campaign_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> CampaignPlan:
    """生成战役计划并落库，保证战役详情页 DAG 与执行使用同一份计划。"""
    repo = CampaignRepository(session, principal.tenant_id)
    campaign = await repo.get_optional(campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "战役不存在")
    plan = await build_campaign_plan(campaign, principal.tenant_id, session)
    campaign.plan_dag = plan.model_dump(mode="json")
    await session.commit()
    await session.refresh(campaign)
    return plan


async def build_campaign_plan(campaign: Campaign, tenant_id: uuid.UUID, session: AsyncSession) -> CampaignPlan:
    """指挥官规则：攻击面优先级 / 历史加权 / 阶段依赖 / 预算分配（PRD 3.3.5.8.1）。"""
    scope = list(campaign.scope) or ["XM-01", "XM-04", "XM-05"]
    intensity = campaign.intensity or Intensity.standard

    # 攻击面摘要：来自 Agent 的基线声明（PRD 3.2.4.1），没有画像时按最保守估计。
    agent = await AgentRepository(session, tenant_id).get_optional(campaign.agent_id)
    declaration = (agent.baseline_declaration if agent is not None else None) or {}
    surface = AgentSurface(
        has_shell=(declaration.get("tool_scope") in {"write", "exec"}),
        has_network=bool(declaration.get("network_enabled")),
        has_write=(declaration.get("tool_scope") in {"write", "exec"}),
        has_rag=bool(declaration.get("has_rag")),
        has_memory=bool(declaration.get("has_long_term_memory")),
        has_multi_agent=False,
        tools=[],
    )

    # 历史加权：取该 Agent 过往攻击记录各类别的成功率，供指挥官排序（PRD 3.3.5.8.1 规则②）。
    records = await AttackRecordRepository(session, tenant_id).for_agent(campaign.agent_id)
    history = HistorySignal(
        category_success=_category_success(records),
        category_streak_fail=_category_streak_fail(records),
    )

    plan = build_plan(
        scope=scope,
        intensity=intensity,
        budget=Budget(**campaign.budget) if campaign.budget else Budget(),
        surface=surface,
        history=history,
    )
    return CampaignPlan.model_validate(plan)


def _category_success(records: Iterable[Any]) -> dict[str, float]:
    """各类别历史成功率（PRD 3.3.5.8.1 规则②：成功手法加权、连败手法降权）。"""
    stats: dict[str, list[int]] = {}
    for record in records:
        code = getattr(record, "category_code", "") or ""
        if not code:
            continue
        slot = stats.setdefault(code, [0, 0])
        slot[1] += 1
        if record.verdict in ("success", "partial"):
            slot[0] += 1
    return {code: hit / total for code, (hit, total) in stats.items() if total}


def _category_streak_fail(records: Iterable[Any]) -> dict[str, int]:
    """按时间正序统计各类别结尾处的连续失败次数。"""
    ordered: dict[str, list[str]] = {}
    for record in sorted(records, key=lambda r: str(getattr(r, "created_at", "") or "")):
        code = getattr(record, "category_code", "") or ""
        if not code:
            continue
        ordered.setdefault(code, []).append(str(record.verdict))
    streak: dict[str, int] = {}
    for code, verdicts in ordered.items():
        count = 0
        for verdict in reversed(verdicts):
            if verdict != "fail":
                break
            count += 1
        if count:
            streak[code] = count
    return streak


@router.post("/{campaign_id}/run")
async def run_campaign(
    campaign_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require("campaign:run"))],
) -> dict[str, Any]:
    """触发战役执行：优先投递 Celery，broker 不可用时内联同步执行（PRD 3.3.5）。"""
    repo = CampaignRepository(session, principal.tenant_id)
    campaign = await repo.get_optional(campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "战役不存在")
    if campaign.status not in ("draft", "scheduled", "tripped", "env_failed"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"当前状态 {campaign.status} 不可执行")
    if not campaign.plan_dag:
        # 没有计划就直接开跑会让详情页停在「暂无战役计划」；这里先补 DAG 再执行（PRD 3.3.5.8.1）
        plan = await build_campaign_plan(campaign, principal.tenant_id, session)
        campaign.plan_dag = plan.model_dump(mode="json")
        await session.commit()
        await session.refresh(campaign)
    campaign.status = "attacking"
    campaign.started_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
    await session.flush()

    try:
        from xian_worker.celery_app import app as celery_app
        from xian_worker.tasks.campaign import run_campaign_task

        if celery_app.connection().ensure_connection(max_retries=0):
            async_result = run_campaign_task.delay({"campaign_id": str(campaign_id)})
            return {"campaign_id": str(campaign_id), "status": "running", "task_id": async_result.id, "mode": "celery"}
    except Exception:
        pass

    from xian_core.redteam import execute_campaign

    try:
        result = await execute_campaign(campaign, session=session, tenant_id=principal.tenant_id)
    except Exception as exc:  # pragma: no cover - 兜底保证状态可回滚
        campaign.status = "failed"
        campaign.plan_dag = {**dict(campaign.plan_dag or {}), "error": str(exc)}
        await session.commit()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"战役执行失败：{exc}") from exc
    campaign.status = "completed"
    campaign.progress = 100
    campaign.ended_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
    await session.commit()
    await session.refresh(campaign)
    return {"campaign_id": str(campaign_id), "status": "completed", "mode": "inline", "result": result.to_dict()}
