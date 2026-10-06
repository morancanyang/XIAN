"""三级裁判：黄金信号回归语料 + 优先级仲裁（AC-03）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from xian_core.judge import JudgeContext, JudgeEngine
from xian_core.judge.rules import RULE_PRIORITY_ORDER, load_rules
from xian_core.schemas.attack import TraceEventIn
from xian_core.schemas.common import enum_str

CORPUS_PATH = Path(__file__).parent / "fixtures" / "judge_corpus" / "golden_signals.json"
MIN_AGREEMENT = 0.85


def _corpus() -> list[dict]:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", _corpus(), ids=lambda c: c["id"])
async def test_golden_signal_regression(case: dict) -> None:
    """逐条语料回归：判定结论与命中规则必须与标注一致。"""
    engine = JudgeEngine()
    events = [TraceEventIn.model_validate(e) for e in case["events"]]
    outcome = await engine.adjudicate(
        events=events,
        context=JudgeContext(
            output_text=case["output_text"],
            canary_values=case["context"].get("canary_values", []),
            session_user_addresses=case["context"].get("session_user_addresses", []),
            baseline_tokens=int(case["context"].get("baseline_tokens", 0)),
            baseline_tool_calls=int(case["context"].get("baseline_tool_calls", 0)),
        ),
    )
    assert enum_str(outcome.verdict) == case["expected_verdict"], case["title"]
    hit_rules = [str(h.get("rule_id", "")) for h in outcome.rule_hits]
    if case["expected_rule"]:
        assert case["expected_rule"] in hit_rules, f"{case['id']} 未命中 {case['expected_rule']}，实际 {hit_rules}"


async def test_golden_no_false_positive_on_benign_traffic() -> None:
    """AC-03 前半：黄金信号零漏报 —— 语料中的正常流量不得误判。"""
    engine = JudgeEngine()
    benign = [c for c in _corpus() if c["id"] == "GS-10"]
    assert benign, "语料缺少正常流量样本"
    for case in benign:
        events = [TraceEventIn.model_validate(e) for e in case["events"]]
        outcome = await engine.adjudicate(
            events=events,
            context=JudgeContext(
                output_text=case["output_text"],
                canary_values=case["context"].get("canary_values", []),
                session_user_addresses=case["context"].get("session_user_addresses", []),
            ),
        )
        assert enum_str(outcome.verdict) == "fail"
        assert outcome.rule_hits == []


async def test_sample_audit_agreement_rate() -> None:
    """AC-03 后半：抽检一致率 >= 85%。"""
    engine = JudgeEngine()
    total = agree = 0
    for case in _corpus():
        events = [TraceEventIn.model_validate(e) for e in case["events"]]
        outcome = await engine.adjudicate(
            events=events,
            context=JudgeContext(
                output_text=case["output_text"],
                canary_values=case["context"].get("canary_values", []),
                session_user_addresses=case["context"].get("session_user_addresses", []),
                baseline_tokens=int(case["context"].get("baseline_tokens", 0)),
                baseline_tool_calls=int(case["context"].get("baseline_tool_calls", 0)),
            ),
        )
        total += 1
        agree += int(enum_str(outcome.verdict) == case["expected_verdict"])
    assert total > 0
    assert agree / total >= MIN_AGREEMENT, f"抽检一致率 {agree}/{total}"


def test_rule_priority_order_covers_all_rules() -> None:
    """每条黄金信号都能在优先级表中找到位置（冲突时可仲裁）。"""
    rules = {r.type for r in load_rules()}
    assert rules.issubset(set(RULE_PRIORITY_ORDER)), rules - set(RULE_PRIORITY_ORDER)


def test_golden_rules_are_deterministic() -> None:
    """同一输入两次判定结论必须一致（可复现是裁判底线）。"""
    import asyncio

    async def _run() -> list[str]:
        engine = JudgeEngine()
        results: list[str] = []
        for case in _corpus():
            events = [TraceEventIn.model_validate(e) for e in case["events"]]
            outcome = await engine.adjudicate(
                events=events,
                context=JudgeContext(
                    output_text=case["output_text"],
                    canary_values=case["context"].get("canary_values", []),
                    session_user_addresses=case["context"].get("session_user_addresses", []),
                    baseline_tokens=int(case["context"].get("baseline_tokens", 0)),
                    baseline_tool_calls=int(case["context"].get("baseline_tool_calls", 0)),
                ),
            )
            results.append(enum_str(outcome.verdict))
        return results

    assert asyncio.run(_run()) == asyncio.run(_run())
