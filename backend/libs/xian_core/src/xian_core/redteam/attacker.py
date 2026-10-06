"""攻击手：多轮策略执行（PRD 3.3.5.8.4 / 3.4.4）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from ..judge import JudgeContext, JudgeEngine
from ..judge.rules import evaluate as golden_evaluate
from ..schemas.attack import TraceEventIn
from ..schemas.common import Verdict
from .strategies import Strategy, get_strategy, render_strategy


def normalize_trace_event(
    raw: dict[str, Any], *, subject_id: UUID, session_id: UUID | None = None
) -> TraceEventIn:
    """把 ChatClient 协议里的观测事件折算为 trace 契约（PRD 3.4.4.8.2）。

    目标 Agent 返回的事件用的是 ``type/role/tool`` 这套接入侧字段名，
    与 ``TraceEventIn`` 的 ``event_type/actor/name`` 不是一套，这里做唯一一处字段映射。
    """
    if not isinstance(raw, dict):
        raw = {}
    return TraceEventIn(
        subject_id=subject_id,
        session_id=session_id,
        event_type=str(raw.get("event_type") or raw.get("type") or "log"),
        actor=str(raw.get("actor") or raw.get("role") or "aut"),
        name=str(raw.get("name") or raw.get("tool") or ""),
        args=dict(raw.get("args", {}) or {}),
        result=dict(raw.get("result", {}) or {}),
        tokens=int(raw.get("tokens", 0) or 0),
        canary_hit=bool(raw.get("canary_hit")) or str(raw.get("type", "")) == "canary_hit",
        latency_ms=int(raw.get("latency_ms", 0) or 0),
    )


@dataclass(slots=True)
class TurnResult:
    turn: int
    prompt: str
    output: str
    events: list[TraceEventIn] = field(default_factory=list)
    verdict: Verdict = Verdict.fail
    tokens: int = 0


@dataclass(slots=True)
class AttackOutcome:
    case_id: str
    category_code: str
    strategy_id: str
    turns: list[TurnResult] = field(default_factory=list)
    verdict: Verdict = Verdict.fail
    confidence: float = 0.0
    rule_hits: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    tokens: int = 0
    escalated: list[str] = field(default_factory=list)
    reason: str = ""
    judge_model: str = ""

    @property
    def turn_count(self) -> int:
        return len(self.turns)


class Attacker:
    """按策略编排多轮对话，逐轮采集 trace 并判定。"""

    def __init__(self, judge: JudgeEngine | None = None) -> None:
        self.judge = judge or JudgeEngine()

    async def execute(
        self,
        client: Any,
        *,
        case_id: str,
        category_code: str,
        payload: str,
        strategy_id: str = "",
        variables: dict[str, str] | None = None,
        max_turns: int = 3,
        session_id: str = "",
        criteria: str = "",
        judge_hint: str = "",
        canary_values: list[str] | None = None,
        subject_id: UUID | None = None,
        signals: list[str] | None = None,
    ) -> AttackOutcome:
        strategy: Strategy | None = get_strategy(strategy_id) if strategy_id else None
        turns: list[TurnResult] = []
        events: list[TraceEventIn] = []
        output_text = ""
        escalation_used: list[str] = []

        for turn in range(1, max(1, max_turns) + 1):
            prompt = self._prompt_for_turn(strategy, payload, turn, variables or {})
            reply = await client.chat(prompt, session_id=session_id)
            output_text = reply.get("output", "")
            turn_events = [
                normalize_trace_event(e, subject_id=subject_id) for e in (reply.get("events", []) or [])
            ]
            turns.append(
                TurnResult(
                    turn=turn,
                    prompt=prompt,
                    output=output_text,
                    events=turn_events,
                    tokens=int(reply.get("tokens", 0)),
                )
            )
            events.extend(turn_events)

            golden = golden_evaluate(
                turn_events,
                output_text=output_text,
                context={"canary_values": canary_values or []},
            )
            if golden.matched:
                return AttackOutcome(
                    case_id=case_id,
                    category_code=category_code,
                    strategy_id=strategy_id,
                    turns=turns,
                    verdict=Verdict.success,
                    confidence=0.99,
                    rule_hits=[
                        {"rule_id": h.rule_id, "severity": h.severity, "detail": h.detail}
                        for h in golden.hits
                    ],
                    evidence=[h.evidence for h in golden.hits],
                    tokens=sum(t.tokens for t in turns),
                    escalated=escalation_used,
                    reason=f"黄金信号命中：{golden.hits[0].detail}",
                    judge_model="golden-rules",
                )

        adjudication = await self.judge.adjudicate(
            events,
            JudgeContext(
                criteria=criteria,
                judge_hint=judge_hint,
                output_text=output_text,
                prompt=prompt,
                signals=list(signals or []),
                canary_values=canary_values or [],
            ),
        )
        return AttackOutcome(
            case_id=case_id,
            category_code=category_code,
            strategy_id=strategy_id,
            turns=turns,
            verdict=adjudication.verdict,
            confidence=adjudication.confidence,
            rule_hits=adjudication.rule_hits,
            evidence=adjudication.evidence,
            tokens=sum(t.tokens for t in turns),
            escalated=escalation_used,
            reason=adjudication.reason,
        )

    def _prompt_for_turn(
        self, strategy: Strategy | None, payload: str, turn: int, variables: dict[str, str]
    ) -> str:
        if strategy is None:
            return payload
        if turn == 1:
            return render_strategy(strategy, variables) or payload
        return payload