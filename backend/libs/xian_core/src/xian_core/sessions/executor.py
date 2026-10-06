"""模式二控制台单轮执行：载荷下发 → 目标应答 → 三级裁判 → 战报卡片（PRD 3.4.4）。

与战役执行器（``xian_core.redteam.runner``）共用同一套 JudgeEngine 与事件总线，
保证自由攻击与自动战役的判定口径一致；services/api 只做协议适配，业务规则集中在此。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..bus import bus, make_event
from ..cases import get_case
from ..db.models import BattleCard, SessionMessage
from ..db.repositories import AgentRepository, BattleCardRepository, SessionMessageRepository
from ..judge import JudgeContext, JudgeEngine
from ..schemas.events import Channel
from ..redteam.attacker import normalize_trace_event
from ..redteam.clients import resolve_agent_client
from ..schemas.attack import TraceEventIn


def utc_now_naive() -> datetime:
    """微秒精度 UTC 朴素时间：SQLite 的 CURRENT_TIMESTAMP 只有秒精度，同秒消息排序会乱。"""
    return datetime.now(UTC).replace(tzinfo=None)


def resolve_console_client(agent: Any) -> Any:
    """按接入方式选择目标客户端（与模式一战役共用同一解析规则）。"""
    return resolve_agent_client(agent)


@dataclass(slots=True)
class ConsoleOutcome:
    """一轮自由攻击的结果摘要（供路由层与事件下发共用）。"""

    output: str = ""
    verdict: str = "fail"
    level: str = ""
    confidence: float = 0.0
    reason: str = ""
    severity: str = "medium"
    rule_hits: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    tokens: int = 0
    case_id: str = ""
    category_code: str = ""
    card_id: str | None = None
    error: str = ""


def _trace_events(agent_id: uuid.UUID, session_id: uuid.UUID, reply: dict[str, Any]) -> list[TraceEventIn]:
    """把目标 Agent 返回的观测事件折算成 trace 契约，供黄金信号规则扫描。"""
    events: list[TraceEventIn] = [
        normalize_trace_event(raw, subject_id=agent_id, session_id=session_id)
        for raw in (reply.get("events", []) or [])
    ]
    events.append(
        TraceEventIn(
            subject_id=agent_id,
            session_id=session_id,
            event_type="output",
            actor="aut",
            name="chat",
            args={},
            result={"output": str(reply.get("output", "") or "")},
            tokens=int(reply.get("tokens", 0) or 0),
            latency_ms=int(reply.get("latency_ms", 0) or 0),
        )
    )
    return events


async def _emit(session_id: uuid.UUID, event_type: str, message: str, payload: dict[str, Any], role: str) -> None:
    """向 sessions:{id} 频道广播事件；WS 中继与历史补发都由 bus 负责。"""
    await bus.publish(
        Channel.session,
        session_id,
        make_event(event_type, role=role, message=message, payload=payload, session_id=str(session_id)),
    )


async def run_console_turn(
    db: AsyncSession,
    *,
    session_row: Any,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: str,
    case_id: str | None = None,
) -> ConsoleOutcome:
    """执行一轮自由攻击：下发载荷 → 落库应答 → 三级裁判 → 命中即出战报卡片。"""
    outcome = ConsoleOutcome(case_id=case_id or "")
    session_id = session_row.id
    case = get_case(case_id) if case_id else None
    if case is not None:
        outcome.category_code = case.category_code

    await _emit(session_id, "log", f"载荷下发：{payload[:120]}", {"content": payload, "case_id": case_id}, "attacker")

    agent = await AgentRepository(db, tenant_id).get_optional(session_row.agent_id)
    if agent is None:
        outcome.error = "目标 Agent 不存在或无权访问"
        await _emit(session_id, "alert", outcome.error, {"case_id": case_id}, "system")
        return outcome

    client = resolve_console_client(agent)
    try:
        reply = await client.chat(payload, session_id=str(session_id))
    except Exception as exc:  # 目标不可达不应让整次发送失败
        outcome.error = f"目标 Agent 调用失败：{exc}"
        await _emit(session_id, "alert", outcome.error, {"case_id": case_id}, "system")
        return outcome

    output = str(reply.get("output", "") or "")
    outcome.output = output
    outcome.tokens = int(reply.get("tokens", 0) or 0)
    await _emit(
        session_id, "log", "目标应答", {"output": output, "latency_ms": reply.get("latency_ms", 0)}, "recon"
    )

    events = _trace_events(session_row.agent_id, session_id, reply)
    for event in events:
        if event.event_type == "tool_call":
            await _emit(
                session_id, "tool_call", f"工具调用 {event.name}", {"tool": event.name, "args": event.args}, "payload"
            )

    # 三级裁判：黄金信号 > 分类器 > LLM 仲裁（PRD 3.6.4.1）
    adjudication = None
    try:
        adjudication = await JudgeEngine().adjudicate(
            events,
            JudgeContext(
                criteria=str((case.success_criteria or {}).get("judge_hint", "")) if case else "",
                judge_hint=case.judge_prompt if case else "",
                output_text=output,
                prompt=payload,
                signals=list((case.success_criteria or {}).get("golden", []) or []) if case else [],
            ),
        )
    except Exception as exc:  # 裁判异常不阻塞会话，降级为未命中
        outcome.error = f"裁判服务异常：{exc}"
        await _emit(session_id, "alert", outcome.error, {"case_id": case_id}, "system")

    if adjudication is not None:
        outcome.verdict = str(getattr(adjudication.verdict, "value", adjudication.verdict))
        outcome.level = str(getattr(adjudication.level, "value", adjudication.level))
        outcome.confidence = float(adjudication.confidence)
        outcome.reason = adjudication.reason
        outcome.severity = adjudication.severity
        outcome.rule_hits = list(adjudication.rule_hits)
        outcome.evidence = list(adjudication.evidence)

    await SessionMessageRepository(db, tenant_id).add(
        SessionMessage(
            session_id=session_id,
            role="assistant",
            content=output,
            payload_ref=case_id or "",
            ts=utc_now_naive(),
        )
    )
    session_row.tokens_used += outcome.tokens
    session_row.last_activity_at = utc_now_naive()

    await _emit(
        session_id,
        "verdict",
        outcome.reason or "判定完成",
        {
            "verdict": outcome.verdict,
            "level": outcome.level,
            "confidence": outcome.confidence,
            "reason": outcome.reason,
            "case_id": case_id or "",
            "category_code": outcome.category_code,
            "rule_hits": outcome.rule_hits,
        },
        "judge",
    )

    if outcome.verdict in ("success", "partial") and not outcome.error:
        card = await BattleCardRepository(db, tenant_id).add(
            BattleCard(
                session_id=session_id,
                user_id=user_id,
                category_id=outcome.category_code or (case_id or "console"),
                severity=outcome.severity,
                evidence=outcome.evidence,
                payload=payload,
                created_at=utc_now_naive(),
            )
        )
        outcome.card_id = str(card.id)
        await _emit(
            session_id,
            "battle_card",
            f"命中 {outcome.category_code or case_id or 'console'}，已生成战报卡片",
            {
                "category_id": outcome.category_code or (case_id or "console"),
                "severity": outcome.severity,
                "payload": payload,
                "evidence": outcome.reason,
                "card_id": outcome.card_id,
                "verdict": outcome.verdict,
            },
            "judge",
        )

    await _emit(session_id, "done", "本轮攻击完成", {"verdict": outcome.verdict, "case_id": case_id}, "system")
    return outcome
