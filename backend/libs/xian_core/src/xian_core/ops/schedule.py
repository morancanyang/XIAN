"""定时巡检与配额计量（PRD 3.8.5.1 / 1.3 配额）。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

CADENCES = {"weekly": 7, "monthly": 30}


@dataclass(slots=True)
class ScanJob:
    job_id: str
    agent_id: str
    cadence: str = "weekly"
    next_run_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    enabled: bool = True

    def due(self, *, now: datetime | None = None) -> bool:
        return self.enabled and (now or datetime.now().astimezone()) >= self.next_run_at

    def advance(self, *, now: datetime | None = None) -> None:
        base = now or datetime.now().astimezone()
        self.next_run_at = base + timedelta(days=CADENCES.get(self.cadence, 7))

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "agent_id": self.agent_id,
            "cadence": self.cadence,
            "next_run_at": self.next_run_at.isoformat(),
            "enabled": self.enabled,
        }


def due_jobs(jobs: Iterable[ScanJob]) -> list[ScanJob]:
    return [j for j in jobs if j.due()]


@dataclass(slots=True)
class QuotaUsage:
    campaigns_used: int = 0
    attacks_used: int = 0
    tokens_used: int = 0
    sandbox_minutes_used: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaigns_used": self.campaigns_used,
            "attacks_used": self.attacks_used,
            "tokens_used": self.tokens_used,
            "sandbox_minutes_used": self.sandbox_minutes_used,
        }


def check_quota(usage: QuotaUsage, limits: dict[str, int]) -> tuple[bool, str]:
    """配额校验（PRD 1.3 配额与限流）。"""
    for key, limit in limits.items():
        if limit <= 0:
            continue
        used = int(getattr(usage, key, 0))
        if used >= limit:
            return False, f"配额 {key} 已用尽：{used}/{limit}"
    return True, "ok"