"""攻击矩阵目录与框架映射（PRD 3.5.4）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..schemas.attack import AttackCategoryOut
from ..schemas.common import Difficulty

ASSET_DIR = Path(__file__).resolve().parent


@dataclass(slots=True)
class CategoryAsset:
    code: str
    name: str
    stage: str
    attack_surface: str
    difficulty: str
    impact: str
    techniques: list[str] = field(default_factory=list)
    detection_signals: list[str] = field(default_factory=list)
    owasp_ref: list[str] = field(default_factory=list)
    atlas_ref: list[str] = field(default_factory=list)
    description: str = ""


@lru_cache(maxsize=1)
def load_categories() -> tuple[CategoryAsset, ...]:
    raw = yaml.safe_load((ASSET_DIR / "categories.yaml").read_text(encoding="utf-8"))
    return tuple(
        CategoryAsset(
            code=c["code"],
            name=c["name"],
            stage=c["stage"],
            attack_surface=c["attack_surface"],
            difficulty=c["difficulty"],
            impact=c["impact"],
            techniques=list(c.get("techniques", [])),
            detection_signals=list(c.get("detection_signals", [])),
            owasp_ref=list(c.get("owasp_ref", [])),
            atlas_ref=list(c.get("atlas_ref", [])),
            description=c.get("description", ""),
        )
        for c in raw["categories"]
    )


def category_codes() -> list[str]:
    return [c.code for c in load_categories()]


def get_category(code: str) -> CategoryAsset | None:
    for cat in load_categories():
        if cat.code == code:
            return cat
    return None


def categories_out() -> list[AttackCategoryOut]:
    return [
        AttackCategoryOut(
            id=c.code,
            code=c.code,
            name=c.name,
            stage=c.stage,
            attack_surface=c.attack_surface,
            difficulty=Difficulty(c.difficulty),
            impact=c.impact,
            techniques=c.techniques,
            detection_signals=c.detection_signals,
            owasp_ref=c.owasp_ref,
            atlas_ref=c.atlas_ref,
        )
        for c in load_categories()
    ]


@lru_cache(maxsize=1)
def load_frameworks() -> dict[str, list[dict[str, Any]]]:
    raw = yaml.safe_load((ASSET_DIR / "frameworks.yaml").read_text(encoding="utf-8"))
    return {f["framework"]: list(f["clauses"]) for f in raw["frameworks"]}


def framework_names() -> list[str]:
    return list(load_frameworks().keys())


def framework_mapping(framework: str) -> list[dict[str, Any]]:
    return load_frameworks().get(framework, [])


def coverage_for(codes: list[str]) -> dict[str, float]:
    """按框架条款计算覆盖进度（PRD 3.5.4.8.1）。"""
    covered = set(codes)
    result: dict[str, float] = {}
    for framework, clauses in load_frameworks().items():
        total = len(clauses)
        if not total:
            continue
        hit = sum(1 for clause in clauses if covered & set(clause["category_ids"]))
        result[framework] = round(hit / total, 4)
    return result