"""回归门禁（PRD 3.8.5.1 / AC-11）：`xian scan` 与 CI 插件的判定内核。

退出码契约（技术方案 contracts.ExitCode）：0 = 通过，1 = 门禁失败，2 = 执行异常。
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from ..errors import ValidationError
from .trend import TrendPoint, regression_failed

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2


@dataclass(slots=True)
class GateRule:
    max_score_drop: int = 5
    fail_on_new_high: bool = True
    min_sec_score: int = 0
    min_baseline_pass_rate: float = 0.8

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> GateRule:
        return cls(
            max_score_drop=int(payload.get("max_score_drop", 5)),
            fail_on_new_high=bool(payload.get("fail_on_new_high", True)),
            min_sec_score=int(payload.get("min_sec_score", 0)),
            min_baseline_pass_rate=float(payload.get("min_baseline_pass_rate", 0.8)),
        )


@dataclass(slots=True)
class GateResult:
    passed: bool
    exit_code: int
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "exit_code": self.exit_code,
            "reasons": list(self.reasons),
            "metrics": dict(self.metrics),
        }


def evaluate(
    *,
    rule: GateRule,
    current_score: int,
    previous_score: int | None = None,
    new_high_count: int = 0,
    baseline_pass_rate: float = 1.0,
) -> GateResult:
    reasons: list[str] = []
    if previous_score is not None:
        drop = previous_score - current_score
        if drop > rule.max_score_drop:
            reasons.append(f"SecScore 跌幅 {drop} 分，超过阈值 {rule.max_score_drop}")
    if rule.fail_on_new_high and new_high_count > 0:
        reasons.append(f"新增 {new_high_count} 个高危问题")
    if current_score < rule.min_sec_score:
        reasons.append(f"SecScore {current_score} 低于底线 {rule.min_sec_score}")
    if baseline_pass_rate < rule.min_baseline_pass_rate:
        reasons.append(
            f"可用性基线通过率 {baseline_pass_rate:.0%} 低于 {rule.min_baseline_pass_rate:.0%}，Agent 可用性受损"
        )
    return GateResult(
        passed=not reasons,
        exit_code=EXIT_PASS if not reasons else EXIT_FAIL,
        reasons=reasons,
        metrics={
            "sec_score": current_score,
            "previous_sec_score": previous_score,
            "new_high_count": new_high_count,
            "baseline_pass_rate": baseline_pass_rate,
        },
    )


def evaluate_from_trend(*, rule: GateRule, points: Iterable[TrendPoint], baseline_pass_rate: float = 1.0) -> GateResult:
    rows = sorted(points, key=lambda p: p.version)
    if not rows:
        return GateResult(passed=True, exit_code=EXIT_PASS, metrics={"points": 0})
    current = rows[-1].sec_score
    previous = rows[-2].sec_score if len(rows) > 1 else None
    result = evaluate(
        rule=rule,
        current_score=current,
        previous_score=previous,
        baseline_pass_rate=baseline_pass_rate,
    )
    if regression_failed(rows, threshold=rule.max_score_drop):
        result.reasons.append("检测到版本间回归（跌幅超阈值）")
        result.passed = False
        result.exit_code = EXIT_FAIL
    return result


def to_sarif(result: GateResult, *, subject: str = "xian-agent") -> dict[str, Any]:
    """SARIF 风格报告，供 CI 平台直接消费（PRD 3.8.5.1）。"""
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "xian-scan", "rules": []}},
                "results": [
                    {
                        "ruleId": "XIAN-GATE",
                        "level": "error",
                        "message": {"text": reason},
                        "locations": [{"physicalLocation": {"artifactLocation": {"uri": subject}}}],
                    }
                    for reason in result.reasons
                ],
                "properties": result.metrics,
            }
        ],
    }


def to_json(result: GateResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def assert_rule(payload: dict[str, Any]) -> GateRule:
    if not isinstance(payload, dict):
        raise ValidationError("门禁规则必须是对象")
    rule = GateRule.from_payload(payload)
    if rule.max_score_drop < 0:
        raise ValidationError("max_score_drop 不能为负")
    if not 0 <= rule.min_baseline_pass_rate <= 1:
        raise ValidationError("min_baseline_pass_rate 必须在 [0,1] 之间")
    return rule