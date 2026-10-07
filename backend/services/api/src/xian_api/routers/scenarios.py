"""场景市场、实例化与蜜标管理（PRD 3.1）。"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from xian_core.db.models import CanaryHit, ScenarioCanary, ScenarioInstance
from xian_core.db.repositories import (
    CanaryHitRepository,
    ScenarioCanaryRepository,
    ScenarioInstanceRepository,
)
from xian_core.sandbox import scan_text
from xian_core.scenarios import (
    build_instance_payload,
    canaries_for_payload,
    filter_templates,
    plant_canaries,
    resolve_template,
    scenario_summary,
)
from xian_core.schemas.scenario import InstanceCreate, ScenarioInstanceOut

from ..deps import Principal, PrincipalDep, SessionDep, require

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
async def market(
    session: SessionDep,
    principal: PrincipalDep,
    difficulty: str | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    """场景市场：卡片列表，支持按难度与考点筛选（PRD 3.1.4.4）。"""
    return [scenario_summary(t.code) for t in filter_templates(difficulty=difficulty, tag=tag)]


@router.get("/instances", response_model=list[ScenarioInstanceOut])
async def list_instances(session: SessionDep, principal: PrincipalDep) -> list[ScenarioInstanceOut]:
    repo = ScenarioInstanceRepository(session, principal.tenant_id)
    rows = await repo.list_by(status="ready")
    return [ScenarioInstanceOut.model_validate(r) for r in rows]


@router.get("/{code}")
async def detail(code: str, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """场景详情：六要素 + 工具权限表 + 蜜标类型（不暴露值）+ 典型攻击链。"""
    return scenario_summary(code)


@router.post("/instances", response_model=ScenarioInstanceOut, status_code=status.HTTP_201_CREATED)
async def instantiate(
    payload: InstanceCreate, session: SessionDep, principal: Annotated[Principal, Depends(require("scenario:write"))]
) -> ScenarioInstanceOut:
    """选用场景并实例化：拉起环境 → 灌假数据 → 植入并登记蜜标 → 布设监控探针。"""
    template = resolve_template(str(payload.scenario_id))
    fields = build_instance_payload(
        template=template,
        tenant_id=principal.tenant_id,
        data_scale=payload.data_scale,
        language=payload.language,
        canary_enhanced=payload.canary_enhanced,
    )
    row = await ScenarioInstanceRepository(session, principal.tenant_id).add(
        ScenarioInstance(
            scenario_id=uuid.uuid5(uuid.NAMESPACE_URL, f"scenario:{template.code}"),
            tenant_id=principal.tenant_id,
            **{k: v for k, v in fields.items() if k not in {"scenario_id", "tenant_id"}},
        )
    )
    planted = plant_canaries(template, instance_id=row.id, enhanced=payload.canary_enhanced)
    canary_repo = ScenarioCanaryRepository(session, principal.tenant_id)
    for canary in planted:
        await canary_repo.add(
            ScenarioCanary(
                tenant_id=principal.tenant_id,
                scenario_id=uuid.uuid5(uuid.NAMESPACE_URL, f"scenario:{template.code}"),
                instance_id=row.id,
                type=canary["type"],
                value=canary["value"],
                plant_location=canary["plant_location"],
                status=canary["status"],
            )
        )
    row.status = "ready"
    await session.commit()
    await session.refresh(row)
    return ScenarioInstanceOut.model_validate(row)


@router.get("/instances/{instance_id}/canaries")
async def list_canaries(instance_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> list[dict[str, Any]]:
    """蜜标清单：仅展示类型与种植位置，不展示值（PRD 3.1.4.4）。"""
    rows = await ScenarioCanaryRepository(session, principal.tenant_id).for_instance(instance_id)
    return canaries_for_payload(
        [{"type": r.type, "plant_location": list(r.plant_location), "status": r.status} for r in rows]
    )


@router.post("/instances/{instance_id}/scan")
async def scan_output(instance_id: uuid.UUID, body: dict, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """蜜标扫描：输出 / egress 请求体 / 工具参数（PRD 3.1.5）。"""
    rows = await ScenarioCanaryRepository(session, principal.tenant_id).for_instance(instance_id)
    values = [r.value for r in rows]
    text = str(body.get("text", ""))
    hits = scan_text(text, canaries=values, via=str(body.get("via", "output")))
    if hits:
        repo = CanaryHitRepository(session, principal.tenant_id)
        for hit in hits:
            await repo.add(
                CanaryHit(
                    tenant_id=principal.tenant_id,
                    canary_id=rows[0].id,
                    instance_id=instance_id,
                    via=hit.via,
                    trace_ref=str(body.get("trace_ref", "")),
                    detail=hit.to_dict(),
                )
            )
        await session.commit()
    return {"hits": [h.to_dict() for h in hits], "count": len(hits)}


@router.delete("/instances/{instance_id}")
async def destroy(instance_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """销毁环境；蜜标台账保留（PRD 3.1.4 后置条件）。"""
    repo = ScenarioInstanceRepository(session, principal.tenant_id)
    row = await repo.get_optional(instance_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "场景实例不存在")
    kept = len(await ScenarioCanaryRepository(session, principal.tenant_id).for_instance(instance_id))
    row.status = "destroyed"
    await session.commit()
    return {
        "instance_id": str(instance_id),
        "environment": "removed",
        "canary_ledger_kept": True,
        "kept_canaries": kept,
        "snapshot_id": str(row.seed_data_snapshot.get("generator_version", "")),
    }
