"""报告中心：九章报告生成、多格式导出、分享与订阅（PRD 3.8.4）。"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, ClassVar

from fastapi import APIRouter, Depends, HTTPException
from xian_core.db.models import Report, ReportExport
from xian_core.cases import get_case
from xian_core.db.repositories import (
    AgentProfileRepository,
    AgentRepository,
    AgentVersionRepository,
    AttackRecordRepository,
    CampaignRepository,
    ReportExportRepository,
    ReportRepository,
)
from xian_core.reports import build_report_payload, create_share, export
from xian_core.schemas.report import ReportOut

from ..deps import Principal, PrincipalDep, SessionDep, require

router = APIRouter(prefix="/reports", tags=["reports"])


class _EmptyAgent:
    """Agent 缺失时的占位视图。"""

    name = "未命名 Agent"
    access_type = "http"
    ownership_verified = False
    baseline_declaration: ClassVar[dict[str, Any]] = {}


_EMPTY_AGENT = _EmptyAgent()


def _agent_view(agent: Any, profile: Any = None) -> dict[str, Any]:
    """渲染报告时使用的 Agent 视图（PRD 3.8.4 报告封面要素 + 第 2 章攻击面清单）。"""
    return {
        "agent_id": str(getattr(agent, "id", "") or ""),
        "name": agent.name,
        "access_type": agent.access_type,
        "endpoint": str(getattr(agent, "endpoint", "") or ""),
        "ownership_verified": agent.ownership_verified,
        "baseline": dict(agent.baseline_declaration or {}),
        "tools": list(getattr(profile, "tools", None) or []),
        "prompt_fragments": list(getattr(profile, "prompt_fragments", None) or []),
        "refusal_boundary": str(getattr(profile, "refusal_boundary", "") or ""),
        "risk_levels": dict(getattr(profile, "risk_levels", None) or {}),
        "canary_types": ["key"],
        "latency_p50": int(getattr(profile, "latency_p50", 0) or 0),
        "latency_p99": int(getattr(profile, "latency_p99", 0) or 0),
        "agent_form": "",
    }


def _record_view(record: Any) -> dict[str, Any]:
    """攻击记录 → 报告渲染所需的最小字段（PRD 3.8.4 第 4-6 章）。"""
    case = get_case(record.case_id or "")
    return {
        "record_id": str(record.id),
        "category_code": record.category_code or "",
        "case_id": record.case_id or "",
        # 用例库里的中文标题，报告里不能只出现 XM-01-001 这种代号
        "case_title": case.title if case is not None else (record.case_id or ""),
        "severity": _severity_of(record),
        "verdict": str(record.verdict or ""),
        "confidence": float(record.confidence or 0.0),
        "strategy": record.strategy or "",
        "turns": int(record.turns or 0),
        "tokens": int(record.tokens or 0),
        "mutation_ops": list(record.mutation_ops or []),
        "golden_rules": list(record.rule_hits or []),
        "evidence": list(record.evidence or []),
        "trace_ref": record.trace_key or str(record.id),
        "scenario_code": (case.scenario_tags[0] if case and case.scenario_tags else ""),
    }


def _severity_of(record: Any) -> str:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    hits = [str(h.get("severity", "low")) for h in (record.rule_hits or []) if isinstance(h, dict)]
    if not hits:
        return "medium" if str(record.verdict) == "success" else "low"
    return max(hits, key=lambda s: order.get(s, 0))


def _version_view(version: Any) -> dict[str, Any]:
    """Agent 版本快照 → 第八章复测对比的一行（PRD 3.7.5 / AC-11）。"""
    return {
        "version": str(getattr(version, "id", "")),
        "prompt_hash": str(getattr(version, "prompt_hash", "") or ""),
        "source": str(getattr(version, "source", "") or ""),
        "created_at": getattr(version, "created_at", None),
        "tools": len(list(getattr(version, "tools_snapshot", None) or [])),
    }


async def _load_subject(
    session: Any, tenant_id: uuid.UUID, subject_type: str, subject_id: uuid.UUID
) -> tuple[Any, list[Any], Any, list[dict[str, Any]]]:
    """按主体类型装载 Agent 视图、记录列表、最新画像与历史版本；主体不存在时抛 404。"""
    if subject_type == "campaign":
        campaigns = await CampaignRepository(session, tenant_id).list_by_id(subject_id)
        if not campaigns:
            raise HTTPException(404, "战役不存在或无权访问")
        campaign = campaigns[0]
        agents = await AgentRepository(session, tenant_id).list_by_id(campaign.agent_id)
        agent = agents[0] if agents else None
        records = await AttackRecordRepository(session, tenant_id).list_by(campaign_id=subject_id)
    else:
        agents = await AgentRepository(session, tenant_id).list_by_id(subject_id)
        if not agents:
            raise HTTPException(404, "Agent 不存在或无权访问")
        agent = agents[0]
        records = await AttackRecordRepository(session, tenant_id).list_by(agent_id=subject_id)
    if agent is None:
        return None, records, None, []
    agent_id = getattr(agent, "id", None)
    profile = await AgentProfileRepository(session, tenant_id).latest(agent_id) if agent_id else None
    versions = [
        _version_view(v) for v in await AgentVersionRepository(session, tenant_id).list_for_agent(agent_id)
    ] if agent_id else []
    return agent, records, profile, versions


async def _delete_report_row(session: SessionDep, tenant_id: uuid.UUID, row: Report) -> None:
    """删报告时连带清掉导出记录：SQLite 不强制外键，留着就是孤儿行。"""
    export_repo = ReportExportRepository(session, tenant_id)
    for artifact in await export_repo.list_by(report_id=row.id):
        await export_repo.delete(artifact)
    await ReportRepository(session, tenant_id).delete(row)


async def _upsert_report(
    session: SessionDep,
    tenant_id: uuid.UUID,
    *,
    subject_type: str,
    subject_id: uuid.UUID,
    payload: dict[str, Any],
) -> Report:
    """同一 subject 只保留一份报告：重新生成是刷新，不是追加。

    之前两个生成端点都直接 insert，点几次"生成报告"就多出几行，
    报告列表里同一个战役重复出现，旧的那份还带着已经修掉的渲染缺陷。
    ReportRepository.for_subject 本来就在，只是从来没被调用过。
    """
    repo = ReportRepository(session, tenant_id)
    row = await repo.for_subject(subject_type, subject_id)
    if row is None:
        return await repo.add(
            Report(
                tenant_id=tenant_id,
                subject_type=subject_type,
                subject_id=subject_id,
                version=1,
                sec_score=int(payload.get("sec_score", 0) or 0),
                grade=str(payload.get("grade", "D") or "D"),
                chapters=dict(payload),
                object_keys={"html": "", "pdf": "", "json": ""},
                share={"expired_at": None, "password": False},
                coverage_pct=float(payload.get("coverage_pct", 0.0) or 0.0),
            )
        )
    # 存量重复行一并清掉：一个主体只保留当前生效的这一份
    for stale in await repo.list_by(subject_type=subject_type, subject_id=subject_id):
        if stale.id != row.id:
            await _delete_report_row(session, tenant_id, stale)
    row.version = int(row.version or 1) + 1
    row.sec_score = int(payload.get("sec_score", 0) or 0)
    row.grade = str(payload.get("grade", "D") or "D")
    row.chapters = dict(payload)
    row.coverage_pct = float(payload.get("coverage_pct", 0.0) or 0.0)
    # 章节内容变了，旧的 html/pdf/json 导出件就是过期快照，指向清掉
    row.object_keys = {"html": "", "pdf": "", "json": ""}
    return row


@router.post("/campaigns/{campaign_id}", response_model=ReportOut)
async def generate_campaign_report(
    campaign_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> ReportOut:
    """按战役生成九章报告（PRD 3.8.4 / AC-05）。"""
    agent, records, profile, versions = await _load_subject(
        session, principal.tenant_id, "campaign", campaign_id
    )
    payload = build_report_payload(
        tenant_id=str(principal.tenant_id),
        subject_type="campaign",
        subject_id=str(campaign_id),
        agent=_agent_view(agent, profile) if agent is not None else _agent_view(_EMPTY_AGENT),
        records=[_record_view(r) for r in records],
        versions=versions,
    )
    row = await _upsert_report(
        session,
        principal.tenant_id,
        subject_type="campaign",
        subject_id=campaign_id,
        payload=payload,
    )
    await session.commit()
    await session.refresh(row)
    return ReportOut.model_validate(row)


@router.post("/agents/{agent_id}", response_model=ReportOut)
async def generate_agent_report(
    agent_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> ReportOut:
    """按 Agent 汇总历史记录生成报告（PRD 3.8.4）。"""
    agent, records, profile, versions = await _load_subject(session, principal.tenant_id, "agent", agent_id)
    payload = build_report_payload(
        tenant_id=str(principal.tenant_id),
        subject_type="agent",
        subject_id=str(agent_id),
        agent=_agent_view(agent, profile),
        records=[_record_view(r) for r in records],
        versions=versions,
    )
    row = await _upsert_report(
        session,
        principal.tenant_id,
        subject_type="agent",
        subject_id=agent_id,
        payload=payload,
    )
    await session.commit()
    await session.refresh(row)
    return ReportOut.model_validate(row)


@router.get("")
async def list_reports(session: SessionDep, principal: PrincipalDep) -> list[dict[str, Any]]:
    rows = await ReportRepository(session, principal.tenant_id).list()
    return [
        {
            "id": str(r.id),
            "subject_type": r.subject_type,
            "subject_id": str(r.subject_id),
            "sec_score": r.sec_score,
            "grade": r.grade,
            "coverage_pct": r.coverage_pct,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/{report_id}", response_model=dict)
async def get_report(report_id: uuid.UUID, session: SessionDep, principal: PrincipalDep) -> dict[str, Any]:
    """报告九章详情（含每条建议的 diff 预览）。"""
    row = await ReportRepository(session, principal.tenant_id).get_optional(report_id)
    if row is None:
        raise HTTPException(404, "报告不存在")
    return {
        "id": str(row.id),
        "subject_type": row.subject_type,
        "subject_id": str(row.subject_id),
        "sec_score": row.sec_score,
        "grade": row.grade,
        "coverage_pct": row.coverage_pct,
        "chapters": dict(row.chapters or {}),
        "object_keys": dict(row.object_keys or {}),
        "share": dict(row.share or {}),
        "created_at": row.created_at,
    }


@router.post("/{report_id}/export")
async def export_report(
    report_id: uuid.UUID,
    body: dict,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require("report:export"))],
) -> dict[str, Any]:
    """多格式导出（HTML/PDF/MD/JSON）+ 脱敏等级（PRD 3.8.4.3）。"""
    row = await ReportRepository(session, principal.tenant_id).get_optional(report_id)
    if row is None:
        raise HTTPException(404, "报告不存在")
    formats = list(body.get("formats", ["html", "json"]))
    level = str(body.get("desensitize_level", "standard"))
    artifacts = export(payload=dict(row.chapters or {}), formats=formats, desensitize_level=level)
    saved: list[dict[str, Any]] = []
    repo = ReportExportRepository(session, principal.tenant_id)
    for artifact in artifacts:
        record = await repo.add(
            ReportExport(
                report_id=row.id,
                format=artifact.fmt,
                desensitize_level=level,
                file_ref=str(artifact.path),
            )
        )
        saved.append(
            {
                "id": str(record.id),
                "format": record.format,
                "file_ref": record.file_ref,
                "bytes": artifact.bytes,
                "desensitize_level": record.desensitize_level,
            }
        )
    await session.commit()
    return {"report_id": str(report_id), "artifacts": saved}


@router.post("/{report_id}/share")
async def share_report(report_id: uuid.UUID, body: dict, principal: PrincipalDep) -> dict[str, Any]:
    link = create_share(
        password=body.get("password"),
        ttl_hours=int(body.get("ttl_hours", 72)),
        watermark=str(body.get("watermark", "XIAN 内部资料")),
    )
    return {"report_id": str(report_id), "share": link.to_dict()}


@router.delete("/{report_id}")
async def delete_report(
    report_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require("report:export"))],
) -> dict[str, Any]:
    """删除报告及其导出件：清理历史重复行与过期快照（PRD 3.8.4）。"""
    row = await ReportRepository(session, principal.tenant_id).get_optional(report_id)
    if row is None:
        raise HTTPException(404, "报告不存在")
    await _delete_report_row(session, principal.tenant_id, row)
    await session.commit()
    return {"id": str(report_id), "deleted": True}
