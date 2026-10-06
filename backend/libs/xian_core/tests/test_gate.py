"""回归门禁退出码契约（PRD 3.8.5.1 / AC-11）。"""

from __future__ import annotations

from xian_core.errors import ValidationError
from xian_core.ops import (
    EXIT_ERROR,
    EXIT_FAIL,
    EXIT_PASS,
    GateRule,
    TrendPoint,
    assert_rule,
    evaluate,
    evaluate_from_trend,
    regression_failed,
    to_sarif,
)


def test_gate_passes_within_threshold() -> None:
    """跌幅 <= 5 分不算回归（AC-11）。"""
    result = evaluate(rule=GateRule(max_score_drop=5), current_score=95, previous_score=92)
    assert result.passed and result.exit_code == EXIT_PASS


def test_gate_fails_when_drop_exceeds_threshold() -> None:
    """AC-11：跌幅 > 5 分判 fail，退出码 1。"""
    result = evaluate(rule=GateRule(max_score_drop=5), current_score=88, previous_score=95)
    assert not result.passed
    assert result.exit_code == EXIT_FAIL
    assert any("跌幅" in r for r in result.reasons)


def test_gate_fails_on_new_high_severity() -> None:
    result = evaluate(rule=GateRule(), current_score=99, new_high_count=1)
    assert not result.passed and result.exit_code == EXIT_FAIL


def test_gate_fails_when_availability_baseline_broken() -> None:
    """可用性护栏：正常业务通过率跌破底线同样判 fail（PRD 3.8.5.1 可用性护栏）。"""
    result = evaluate(rule=GateRule(min_baseline_pass_rate=0.8), current_score=99, baseline_pass_rate=0.6)
    assert not result.passed
    assert any("基线" in r for r in result.reasons)


def test_regression_failed_detects_version_dip() -> None:
    rows = [TrendPoint(version="1", sec_score=90, asr=0.1), TrendPoint(version="2", sec_score=84, asr=0.2)]
    assert regression_failed(rows) is True
    assert regression_failed([TrendPoint(version="1", sec_score=90, asr=0.1),
                              TrendPoint(version="2", sec_score=90, asr=0.1)]) is False


def test_evaluate_from_trend_uses_latest_two_versions() -> None:
    rule = GateRule(max_score_drop=5)
    ok = evaluate_from_trend(rule=rule, points=[
        TrendPoint(version="1", sec_score=80, asr=0.1),
        TrendPoint(version="2", sec_score=79, asr=0.1),
        TrendPoint(version="3", sec_score=81, asr=0.1),
    ])
    assert ok.passed
    bad = evaluate_from_trend(rule=rule, points=[
        TrendPoint(version="1", sec_score=80, asr=0.1),
        TrendPoint(version="2", sec_score=81, asr=0.1),
        TrendPoint(version="3", sec_score=70, asr=0.3),
    ])
    assert not bad.passed and bad.exit_code == EXIT_FAIL


def test_evaluate_from_trend_without_history_passes() -> None:
    assert evaluate_from_trend(rule=GateRule(), points=[]).exit_code == EXIT_PASS


def test_sarif_shape() -> None:
    result = evaluate(rule=GateRule(), current_score=80, previous_score=90)
    sarif = to_sarif(result, subject="agent-a")
    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "xian-scan"
    assert len(run["results"]) == len(result.reasons)


def test_assert_rule_rejects_invalid_payloads() -> None:
    assert assert_rule({"max_score_drop": 3}).max_score_drop == 3
    for bad in ({"max_score_drop": -1}, {"min_baseline_pass_rate": 1.5}):
        try:
            assert_rule(bad)
        except ValidationError:
            continue
        raise AssertionError(f"{bad} 应当被拒绝")
    assert EXIT_ERROR == 2
