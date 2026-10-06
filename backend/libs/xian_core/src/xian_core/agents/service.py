"""Agent 资产服务：接入向导、状态机、画像与推荐（PRD 3.2）。"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from ..errors import NotFoundError, PermissionDenied, ValidationError
from ..identity import assert_verified, make_nonce, verify_dns, verify_image_digest
from ..scenarios import available_scenarios, recommend_for_agent
from ..schemas.agent import (
    AgentCreate,
    AgentOut,
    AgentUpdate,
    AgentVersionCreate,
    BaselineDeclaration,
    ScenarioRecommendation,
)
from ..schemas.common import enum_str
from .change_detect import ChangeSignal, detect
from .versions import VersionSnapshot, diff_versions, from_create

# Agent 状态机（技术方案 2.2）：未验证 → 已归属验证 → 演练中 → 已归档 / 下线
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "unverified": {"active", "archived", "offline"},
    "active": {"testing", "offline", "archived"},
    "testing": {"active", "offline"},
    "offline": {"active", "archived"},
    "archived": set(),
}

STATUS_HINTS = {
    "unverified": "已创建，等待归属校验与连通性探测通过",
    "active": "已归属验证，可作为演练目标",
    "testing": "演练进行中",
    "offline": "已下线，拒绝新演练，历史报告保留",
    "archived": "已归档，仅保留历史成绩",
}


def assert_transition(current: str, target: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValidationError(f"Agent 状态不允许从 {current} 迁移到 {target}")


def to_out(row: Any) -> AgentOut:
    return AgentOut(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        access_type=row.access_type,  # type: ignore[arg-type]
        endpoint=row.endpoint,
        description=row.description,
        ownership_verified=row.ownership_verified,
        ownership_method=row.ownership_method,  # type: ignore[arg-type]
        baseline_declaration=row.baseline_declaration or {},
        status=row.status,  # type: ignore[arg-type]
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def build_agent(tenant_id: uuid.UUID, payload: AgentCreate) -> dict[str, Any]:
    """接入向导第一步：落库 Agent 资产（状态 pending，未归属验证）。"""
    return {
        "tenant_id": tenant_id,
        "name": payload.name,
        "access_type": enum_str(payload.access_type),
        "endpoint": payload.endpoint,
        "description": payload.description,
        "baseline_declaration": payload.baseline_declaration.model_dump(),
        "ownership_verified": False,
        "status": "unverified",
    }


def apply_update(row: Any, payload: AgentUpdate) -> dict[str, Any]:
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        target = data["status"].value if hasattr(data["status"], "value") else data["status"]
        assert_transition(row.status, target)
    if "baseline_declaration" in data and data["baseline_declaration"] is not None:
        data["baseline_declaration"] = BaselineDeclaration(**data["baseline_declaration"]).model_dump()
    data["updated_at"] = datetime.now().astimezone()
    return data


def start_verification(
    agent_id: uuid.UUID, method: str, target: str, *, nonce: str | None = None
) -> dict[str, Any]:
    """生成校验值并返回操作指引（PRD 3.2.4.8.1）。

    ``nonce`` 为空时新生成；传入既有 nonce 表示复用上次未通过的校验值，
    这样用户完成 DNS 配置后再次触发校验，比对的是同一条记录。
    """
    nonce = nonce or make_nonce()
    if method == "dns_txt":
        instruction = _dns_instruction(target, nonce)
    elif method == "image_digest":
        instruction = {
            "method": "image_digest",
            "target": target,
            "nonce": nonce,
            "hint": "请提供镜像 digest，或允许平台读取 registry RepoDigests。",
        }
    else:
        raise ValidationError(f"不支持的归属校验方式 {method}")
    return {
        "agent_id": str(agent_id),
        "method": method,
        "target": target,
        "nonce": nonce,
        "instruction": instruction,
    }


def _dns_instruction(domain: str, nonce: str) -> dict[str, str]:
    from ..identity import build_dns_instruction

    return build_dns_instruction(domain, nonce)


def run_verification(*, method: str, target: str, nonce: str, observed_digest: str | None = None) -> dict[str, Any]:
    if method == "dns_txt":
        return verify_dns(target, nonce)
    return verify_image_digest(target, observed_digest)


def record_verification(agent_id: uuid.UUID, result: dict[str, Any]) -> dict[str, Any]:
    from ..schemas.common import OwnershipResult


    ok = result.get("result") == OwnershipResult.verified.value
    return {
        "agent_id": agent_id,
        "type": result.get("method"),
        "target": result.get("target", ""),
        "nonce": result.get("nonce", ""),
        "result": result.get("result"),
        "detail": result.get("reason", ""),
        "agent_status": "active" if ok else "unverified",
        "agent_ownership_verified": ok,
    }


def assert_attackable(agent: Any) -> None:
    """模式一目标必须是 active 且归属已验证（PRD 3.2.4.8.1 / AC-09）。"""
    if agent.status == "archived":
        raise PermissionDenied("Agent 已归档，不能作为演练目标")
    if agent.status == "offline":
        raise PermissionDenied("Agent 已下线，请先恢复后再发起演练")
    if not agent.ownership_verified:
        assert_verified({"result": "failed"})


def build_health_record(agent_id: uuid.UUID, report: Any) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "latency_ms": report.latency_ms,
        "trace_sample": report.trace_sample,
        "result": report.result,
        "detail": "; ".join(report.hints),
    }


def build_profile(
    agent_id: uuid.UUID,
    *,
    tools: Iterable[dict[str, Any]],
    risk_levels: dict[str, str],
    refusal_boundary: str,
    prompt_fragments: Iterable[str],
    fingerprint: dict[str, Any],
    latency_p50: int,
    latency_p99: int,
    lang_prefs: Iterable[str],
) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "tools": list(tools),
        "risk_levels": dict(risk_levels),
        "refusal_boundary": refusal_boundary,
        "prompt_fragments": list(prompt_fragments),
        "fingerprint": dict(fingerprint),
        "latency_p50": latency_p50,
        "latency_p99": latency_p99,
        "lang_prefs": list(lang_prefs),
    }


def recommend_scenarios(*, tools: Iterable[str], declaration: BaselineDeclaration) -> list[ScenarioRecommendation]:
    """场景匹配推荐（PRD 3.1.4.8.1）。"""
    raw = recommend_for_agent(
        tools=tools,
        has_memory=declaration.has_long_term_memory,
        has_rag=declaration.has_rag,
    )
    code_to_id = {s["id"]: str(uuid.uuid5(uuid.NAMESPACE_URL, f"scenario:{s['id']}")) for s in available_scenarios()}
    return [
        ScenarioRecommendation(
            scenario_id=uuid.UUID(code_to_id.get(item["scenario_id"], str(uuid.uuid4()))),
            scenario_code=item["scenario_id"],
            name=item["scenario_name"],
            difficulty=item["difficulty"],  # type: ignore[arg-type]
            match_score=item["match_score"],
            matched_tools=item["matched_tools"],
            reason="；".join(item["reasons"]),
        )
        for item in raw
    ]


def create_version(agent_id: uuid.UUID, payload: AgentVersionCreate, *, prompt: str = "") -> VersionSnapshot:
    return from_create(str(agent_id), payload, prompt=prompt)


def evaluate_change(previous: VersionSnapshot | None, current: VersionSnapshot) -> ChangeSignal | None:
    return detect(previous, current)


def latest_snapshot_from(rows: Iterable[Any]) -> VersionSnapshot | None:
    """把 AgentVersion ORM 行还原为快照对象（供 diff 使用）。"""
    rows = list(rows)
    if not rows:
        return None
    row = rows[0]
    return VersionSnapshot(
        agent_id=str(row.agent_id),
        prompt="",
        tools=list(row.tools_snapshot or []),
        model_params=dict(row.model_config or {}),
        source=row.source,
        prompt_hash_override=str(row.prompt_hash or ""),
    )


def summarize_diff(previous: VersionSnapshot | None, current: VersionSnapshot) -> dict[str, Any]:
    return diff_versions(previous, current)


def find_agent_or_404(rows: Iterable[Any]) -> Any:
    rows = list(rows)
    if not rows:
        raise NotFoundError("Agent 不存在或无权访问")
    return rows[0]