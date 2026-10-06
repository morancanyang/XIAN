"""报告订阅与巡检推送（PRD 3.8.4.8.1）。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

CADENCES = ("weekly", "monthly")
CHANNELS = ("email", "webhook", "inapp")


@dataclass(slots=True)
class Subscription:
    user_id: str
    cadence: str
    channels: list[str] = field(default_factory=list)
    recipients: list[str] = field(default_factory=list)
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "cadence": self.cadence,
            "channels": list(self.channels),
            "recipients": list(self.recipients),
            "active": self.active,
        }


def validate(subscription: Subscription) -> Subscription:
    if subscription.cadence not in CADENCES:
        raise ValueError(f"订阅频率仅支持 {CADENCES}")
    bad = [c for c in subscription.channels if c not in CHANNELS]
    if bad:
        raise ValueError(f"不支持的推送渠道 {bad}")
    if not subscription.recipients:
        raise ValueError("订阅必须至少有一个接收人")
    return subscription


def build_digest(*, period: str, campaigns: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """周期摘要：SecScore 均值、新增高危、演练次数（PRD 3.8.4.8.1）。"""
    rows = list(campaigns)
    scores = [float(c.get("sec_score", 0)) for c in rows]
    highs = [c for c in rows if any(r.get("severity") in {"critical", "high"} for r in c.get("high_risks", []))]
    return {
        "period": period,
        "campaign_count": len(rows),
        "avg_sec_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "new_high_risks": len(highs),
        "subjects": sorted({str(c.get("agent_name", "")) for c in rows if c.get("agent_name")}),
    }


def should_alert(digest: dict[str, Any], *, threshold_high: int = 1) -> bool:
    """新增高危即时告警（PRD 3.8.5.1 定时巡检）。"""
    return int(digest.get("new_high_risks", 0)) >= threshold_high