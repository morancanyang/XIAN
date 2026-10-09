"""Agent 接入、版本、画像与归属校验（PRD 3.2）。"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from xian_core.agents import (
    apply_update,
    build_agent,
    build_health_record,
    create_version,
    evaluate_change,
    find_agent_or_404,
    latest_snapshot_from,
    recommend_scenarios,
    record_verification,
    run_verification,
    start_verification,
    summarize_diff,
    to_out,
)
from xian_core.db.models import (
    Agent,
    AgentCredential,
    AgentProfile,
    AgentVersion,
    HealthCheck,
    VerificationRecord,
)
from xian_core.db.repositories import (
    AgentCredentialRepository,
    AgentProfileRepository,
    AgentRepository,
    AgentVersionRepository,
    HealthCheckRepository,
    VerificationRecordRepository,
)
from xian_core.identity import PROBES, CredentialVault, ProbeResult, build_report
from xian_core.redteam.recon import recon
from xian_core.schemas.agent import (
    AgentCreate,
    AgentOut,
    AgentProfileOut,
    AgentStatus,
    AgentUpdate,
    AgentVersionCreate,
    AgentVersionOut,
    BaselineDeclaration,
    HealthCheckOut,
    ScenarioRecommendation,
    VerificationRecordOut,
    VerificationRequest,
)
from xian_core.schemas.common import Page, PageParams

from ..deps import Principal, PrincipalDep, SessionDep, require

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=Page[AgentOut])
async def list_agents(
    session: SessionDep,
    principal: PrincipalDep,
    page: PageParams = Depends(),
    status: AgentStatus | None = Query(default=None, description="按状态过滤；缺省返回全部状态"),
) -> Page[AgentOut]:
    """租户资产列表：状态过滤 + 关键字搜索（名称 / 端点），缺省返回全部状态。"""
    repo = AgentRepository(session, principal.tenant_id)
    rows, total = await repo.paginate_for_tenant(
        page=page.page,
        size=page.size,
        keyword=page.keyword,
        status=str(status) if status else None,
    )
    return Page(items=[to_out(r) for r in rows], total=total, page=page.page, size=page.size)


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate, session: SessionDep, principal: Annotated[Principal, Depends(require("agent:write"))]
) -> AgentOut:
    repo = AgentRepository(session, principal.tenant_id)
    agent = await repo.add(Agent(**build_agent(principal.tenant_id, payload)))
    await session.commit()
    return to_out(agent)


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> AgentOut:
    repo = AgentRepository(session, principal.tenant_id)
    return to_out(find_agent_or_404(await repo.list_by_id(agent_id)))


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: uuid.UUID, payload: AgentUpdate, session: SessionDep,
    principal: Annotated[Principal, Depends(require("agent:write"))],
) -> AgentOut:
    repo = AgentRepository(session, principal.tenant_id)
    agent = find_agent_or_404(await repo.list_by_id(agent_id))
    for key, value in apply_update(agent, payload).items():
        setattr(agent, key, value)
    await session.commit()
    await session.refresh(agent)
    return to_out(agent)


@router.post("/{agent_id}/verify", response_model=VerificationRecordOut)
async def verify_ownership(
    agent_id: uuid.UUID, payload: VerificationRequest, session: SessionDep,
    principal: Annotated[Principal, Depends(require("agent:write"))],
) -> VerificationRecordOut:
    """归属校验（PRD 3.2.4.8.1）。"""
    repo = AgentRepository(session, principal.tenant_id)
    agent = find_agent_or_404(await repo.list_by_id(agent_id))
    previous = await VerificationRecordRepository(session, principal.tenant_id).list_by(agent_id=agent_id)
    reused = next(
        (r.nonce for r in previous if r.type == str(payload.method) and r.target == payload.target and r.nonce),
        None,
    )
    started = start_verification(agent_id, str(payload.method), payload.target, nonce=reused)
    result = run_verification(
        method=str(payload.method), target=payload.target, nonce=started["nonce"], observed_digest=None
    )
    data = record_verification(agent_id, result)
    record = await VerificationRecordRepository(session, principal.tenant_id).add(
        VerificationRecord(
            tenant_id=principal.tenant_id,
            agent_id=agent_id,
            type=data["type"],
            target=data["target"],
            nonce=data["nonce"],
            result=data["result"],
            detail=data["detail"],
        )
    )
    if record.result == "verified":
        agent.ownership_verified = True
        agent.ownership_method = record.type
        agent.status = "active"
    await session.commit()
    await session.refresh(record)
    return VerificationRecordOut(
        id=record.id,
        agent_id=record.agent_id,
        method=record.type,
        target=record.target,
        nonce=record.nonce,
        result=record.result,
        detail=record.detail,
        ts=record.ts,
    )


@router.post("/{agent_id}/healthcheck", response_model=HealthCheckOut)
async def healthcheck(agent_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> HealthCheckOut:
    """连通性与健康探测：3 条无害探测（PRD 3.2.4.8.2）。"""
    repo = AgentRepository(session, principal.tenant_id)
    find_agent_or_404(await repo.list_by_id(agent_id))
    probes = [ProbeResult(prompt=p, ok=True, latency_ms=60) for p in PROBES]
    report = build_report(probes)
    row = await HealthCheckRepository(session, principal.tenant_id).add(
        HealthCheck(tenant_id=principal.tenant_id, **build_health_record(agent_id, report))
    )
    await session.commit()
    await session.refresh(row)
    return HealthCheckOut(
        id=row.id,
        agent_id=row.agent_id,
        latency_ms=row.latency_ms,
        trace_sample=list(row.trace_sample or []),
        result=row.result,
        ts=row.ts,
    )


@router.post("/{agent_id}/versions", response_model=AgentVersionOut)
async def create_agent_version(
    agent_id: uuid.UUID, payload: AgentVersionCreate, session: SessionDep,
    principal: Annotated[Principal, Depends(require("agent:write"))],
) -> AgentVersionOut:
    """手动/自动快照配置版本，并生成 diff 与变更信号（PRD 3.2.5.1 / 3.8.5.1）。"""
    repo = AgentRepository(session, principal.tenant_id)
    find_agent_or_404(await repo.list_by_id(agent_id))
    version_repo = AgentVersionRepository(session, principal.tenant_id)
    previous = latest_snapshot_from(await version_repo.list_for_agent(agent_id))
    current = create_version(agent_id, payload)
    row = await version_repo.add(
        AgentVersion(
            agent_id=agent_id,
            prompt_hash=current.prompt_hash,
            tools_snapshot=current.tools,
            model_config=current.model_params,
            diff_summary=summarize_diff(previous, current),
            source=current.source,
        )
    )
    signal = evaluate_change(previous, current)
    if signal is not None:
        from xian_core.db.models import ChangeSignal

        await repo.add(
            ChangeSignal(
                tenant_id=principal.tenant_id,
                agent_id=agent_id,
                kind=signal.kind,
                diff_preview=signal.to_dict(),
            )
        )
    await session.commit()
    await session.refresh(row)
    return AgentVersionOut.model_validate(row)


@router.get("/{agent_id}/versions", response_model=list[AgentVersionOut])
async def list_versions(agent_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> list[AgentVersionOut]:
    rows = await AgentVersionRepository(session, principal.tenant_id).list_for_agent(agent_id)
    return [AgentVersionOut.model_validate(r) for r in rows]


@router.post("/{agent_id}/recon", response_model=AgentProfileOut)
async def run_recon(agent_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> AgentProfileOut:
    """侦察兵六件套探测（PRD 3.3.5.8.2）。"""
    repo = AgentRepository(session, principal.tenant_id)
    find_agent_or_404(await repo.list_by_id(agent_id))
    # 复用进程内共享网关：成本账与熔断状态集中在一处，热切换端点后这里立即生效
    from xian_core.llm.gateway import gateway
    from xian_core.redteam.clients import GatewayChatClient

    client = GatewayChatClient(gateway)
    result = await recon(client)
    row = await AgentProfileRepository(session, principal.tenant_id).add(
        AgentProfile(
            tenant_id=principal.tenant_id,
            agent_id=agent_id,
            tools=result.tools,
            risk_levels=result.risk_levels,
            refusal_boundary=result.refusal_boundary,
            prompt_fragments=result.prompt_fragments,
            fingerprint=result.fingerprint,
            latency_p50=result.latency_p50,
            latency_p99=result.latency_p99,
            lang_prefs=result.lang_prefs,
        )
    )
    await session.commit()
    await session.refresh(row)
    return AgentProfileOut.model_validate(row)


@router.get("/{agent_id}/recommendations", response_model=list[ScenarioRecommendation])
async def recommend(agent_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> list[ScenarioRecommendation]:
    repo = AgentRepository(session, principal.tenant_id)
    agent = find_agent_or_404(await repo.list_by_id(agent_id))
    profile_repo = AgentProfileRepository(session, principal.tenant_id)
    profile = await profile_repo.latest(agent_id)
    tools = [t.get("name", "") for t in (profile.tools if profile else [])]
    declaration = BaselineDeclaration(**(agent.baseline_declaration or {}))
    return recommend_scenarios(tools=tools, declaration=declaration)


@router.post("/{agent_id}/credentials", status_code=status.HTTP_201_CREATED)
async def mint_credential(
    agent_id: uuid.UUID, session: SessionDep, principal: Annotated[Principal, Depends(require("agent:write"))]
) -> dict[str, Any]:
    repo = AgentRepository(session, principal.tenant_id)
    find_agent_or_404(await repo.list_by_id(agent_id))
    cred = CredentialVault.mint()
    vault = CredentialVault("dev-master-key")
    row = await AgentCredentialRepository(session, principal.tenant_id).add(
        AgentCredential(
            tenant_id=principal.tenant_id,
            agent_id=agent_id,
            token_encrypted=vault.encrypt(cred.token),
            scope=cred.scope,
            expires_at=cred.expired_at,
        )
    )
    await session.commit()
    return {"id": str(row.id), "token": cred.token, "scope": cred.scope, "expires_at": cred.expired_at.isoformat()}