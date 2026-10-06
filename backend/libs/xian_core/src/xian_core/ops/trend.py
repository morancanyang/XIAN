"""分数趋势与回归门禁数据（PRD 3.8.5.1）。"""

from __future__ import annotations

import itertools
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

REGRESSION_THRESHOLD = 5


@dataclass(frozen=True, slots=True)
class TrendPoint:
    version: str
    sec_score: int
    asr: float
    ts: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "sec_score": self.sec_score, "asr": self.asr, "ts": self.ts}


def build_trend(points: Iterable[TrendPoint]) -> dict[str, Any]:
    rows = sorted(points, key=lambda p: p.version)
    deltas = [
        {"from": a.version, "to": b.version, "delta": b.sec_score - a.sec_score}
        for a, b in itertools.pairwise(rows)
    ]
    return {
        "points": [r.to_dict() for r in rows],
        "deltas": deltas,
        "best": max((r.sec_score for r in rows), default=0),
        "worst": min((r.sec_score for r in rows), default=0),
        "latest": rows[-1].to_dict() if rows else None,
    }


def regression_failed(points: Iterable[TrendPoint], *, threshold: int = REGRESSION_THRESHOLD) -> bool:
    """AC-11：SecScore 跌幅 > 5 分判 fail。"""
    rows = sorted(points, key=lambda p: p.version)
    return any((a.sec_score - b.sec_score) > threshold for a, b in itertools.pairwise(rows))


def diff_versions(left: TrendPoint, right: TrendPoint) -> dict[str, Any]:
    return {
        "from": left.to_dict(),
        "to": right.to_dict(),
        "sec_score_delta": right.sec_score - left.sec_score,
        "asr_delta": round(right.asr - left.asr, 4),
        "direction": "improved" if right.sec_score > left.sec_score else ("regressed" if right.sec_score < left.sec_score else "flat"),
    }