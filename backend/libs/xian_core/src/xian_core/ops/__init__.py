"""分数趋势、回归门禁、定时巡检与配额（PRD 3.8.5）。"""

from .gate import (
    EXIT_ERROR,
    EXIT_FAIL,
    EXIT_PASS,
    GateResult,
    GateRule,
    assert_rule,
    evaluate,
    evaluate_from_trend,
    to_json,
    to_sarif,
)
from .schedule import CADENCES, QuotaUsage, ScanJob, check_quota, due_jobs
from .trend import REGRESSION_THRESHOLD, TrendPoint, build_trend, diff_versions, regression_failed

__all__ = [
    "CADENCES",
    "EXIT_ERROR",
    "EXIT_FAIL",
    "EXIT_PASS",
    "REGRESSION_THRESHOLD",
    "GateResult",
    "GateRule",
    "QuotaUsage",
    "ScanJob",
    "TrendPoint",
    "assert_rule",
    "build_trend",
    "check_quota",
    "diff_versions",
    "due_jobs",
    "evaluate",
    "evaluate_from_trend",
    "regression_failed",
    "to_json",
    "to_sarif",
]