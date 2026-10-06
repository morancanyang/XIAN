"""多轮策略库与升级路径（PRD 3.3.5.8.4）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from ...cases import render_payload

ASSET = Path(__file__).resolve().parent / "library.yaml"


@dataclass(slots=True)
class Strategy:
    id: str
    name: str
    categories: list[str] = field(default_factory=list)
    turns: int = 2
    description: str = ""
    escalation: list[str] = field(default_factory=list)
    template: str = ""


@lru_cache(maxsize=1)
def load_strategies() -> tuple[Strategy, ...]:
    raw = yaml.safe_load(ASSET.read_text(encoding="utf-8")) or {}
    return tuple(
        Strategy(
            id=s["id"],
            name=s["name"],
            categories=list(s.get("categories", [])),
            turns=int(s.get("turns", 2)),
            description=s.get("description", ""),
            escalation=list(s.get("escalation", [])),
            template=s.get("template", ""),
        )
        for s in raw.get("strategies", [])
    )


def strategies_for_category(category_code: str) -> list[Strategy]:
    return [s for s in load_strategies() if category_code in s.categories]


def get_strategy(strategy_id: str) -> Strategy | None:
    for s in load_strategies():
        if s.id == strategy_id:
            return s
    return None


def render_strategy(strategy: Strategy, variables: dict[str, str]) -> str:
    return render_payload(strategy.template, variables)


def escalation_ops(strategy: Strategy) -> list[str]:
    """失败后的升级路径：返回可叠加的变异算子（PRD 3.3.5.8.4）。"""
    return list(strategy.escalation)