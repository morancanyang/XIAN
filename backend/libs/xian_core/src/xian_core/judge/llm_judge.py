"""LLM-as-judge：三级判定的第三级，结构化 JSON 输出 + 双裁判投票 + 反注入（PRD 3.6.4.8.2）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..llm.gateway import LLMGateway
from ..llm.prompts import (
    JUDGE_PROMPT_VERSION,
    JUDGE_SYSTEM_V1,
    JUDGE_USER_V1,
)
from ..schemas.common import JudgeLevel, Verdict

VERDICT_MAP = {
    "success": Verdict.success,
    "partial": Verdict.partial,
    "fail": Verdict.fail,
    "unavailable": Verdict.unavailable,
}


@dataclass(slots=True)
class JudgeResult:
    verdict: Verdict
    confidence: float
    rule_hits: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    judge_model: str = ""
    level: JudgeLevel = JudgeLevel.llm
    degraded: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


def build_trace_text(events: list[Any], output_text: str) -> str:
    """把观测事件流与输出组装成裁判上下文，带行号以便证据引用（PRD 3.6.4.7）。"""
    lines: list[str] = []
    for idx, ev in enumerate(events, start=1):
        lines.append(
            f"[L{idx}] type={ev.event_type} actor={ev.actor} name={ev.name} "
            f"args={json.dumps(ev.args, ensure_ascii=False, default=str)} "
            f"result={json.dumps(ev.result, ensure_ascii=False, default=str)} "
            f"tokens={ev.tokens} canary_hit={ev.canary_hit}"
        )
    if output_text:
        lines.append(f"[L{len(lines) + 1}] type=output actor=aut content={output_text}")
    return "\n".join(lines)


def parse_judge_json(payload: dict[str, Any], *, model: str = "") -> JudgeResult:
    """校验裁判 JSON schema；不合规时抛错由调用方降级（PRD 3.6.4.6）。"""
    verdict = VERDICT_MAP.get(str(payload.get("verdict", "fail")).lower())
    if verdict is None:
        raise ValueError(f"非法 verdict: {payload.get('verdict')!r}")
    confidence = float(payload.get("confidence", 0.0) or 0.0)
    confidence = min(max(confidence, 0.0), 1.0)
    return JudgeResult(
        verdict=verdict,
        confidence=confidence,
        rule_hits=list(payload.get("rule_hits", []) or []),
        evidence=list(payload.get("evidence", []) or []),
        reason=str(payload.get("reason", ""))[:200],
        judge_model=model,
        raw=payload,
    )


async def llm_judge(
    gateway: LLMGateway,
    *,
    criteria: str,
    judge_hint: str,
    trace_text: str,
    model: str | None = None,
) -> JudgeResult:
    prompt = JUDGE_USER_V1.format(criteria=criteria or "（未提供）", judge_hint=judge_hint or "（无）", trace=trace_text)
    resp = await gateway.complete(
        prompt, role="judge", system=JUDGE_SYSTEM_V1, temperature=0.0, max_tokens=600, model=model
    )
    try:
        return parse_judge_json(resp.json(), model=resp.model)
    except ValueError:
        # 输出不合规 JSON 时重试 1 次，仍失败由上层降级为分类器结论（PRD 3.6.4.6）
        retry = await gateway.complete(
            prompt + "\n\n上一次输出不是合法 JSON，请只输出 JSON。",
            role="judge",
            system=JUDGE_SYSTEM_V1,
            temperature=0.0,
            max_tokens=600,
            model=model,
        )
        return parse_judge_json(retry.json(), model=retry.model)


def vote(results: list[JudgeResult]) -> JudgeResult:
    """双裁判投票：分歧时取高置信度一侧并标记需人工复核（PRD 3.6.4.1）。"""
    if not results:
        return JudgeResult(verdict=Verdict.unavailable, confidence=0.0, reason="无裁判结果")
    if len(results) == 1:
        return results[0]
    success = [r for r in results if r.verdict in (Verdict.success, Verdict.partial)]
    agree = len(success) in (0, len(results))
    winner = max(results, key=lambda r: r.confidence)
    merged = JudgeResult(
        verdict=winner.verdict,
        confidence=winner.confidence,
        rule_hits=[h for r in results for h in r.rule_hits],
        evidence=[e for r in results for e in r.evidence],
        reason="；".join(r.reason for r in results if r.reason),
        judge_model="+".join(sorted({r.judge_model for r in results if r.judge_model})),
        raw={"votes": [r.raw for r in results], "agree": agree},
    )
    if not agree:
        merged.raw["needs_human_review"] = True
    return merged


JUDGE_PROMPT_VERSION_TAG = JUDGE_PROMPT_VERSION