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


def normalize_stage(raw_stage: str) -> str:
    """把类别声明的 stage 文本归一为规范阶段键（六段 kill chain）。

    计划 DAG 与前端 PlanPreview 的列都用这六段：初始执行与载荷投递分开，
    这样"载荷投递→初始执行"这类复合阶段能落到最先发生的那一列。
    """
    text = (raw_stage or "").lower()
    if "侦察" in raw_stage or "recon" in text:
        return "recon"
    if "渗出" in raw_stage or "exfiltrat" in text:
        return "exfiltration"
    if "提权" in raw_stage or "权限" in raw_stage or "escalat" in text:
        return "privilege_escalation"
    if "持久化" in raw_stage or "横向" in raw_stage:
        return "privilege_escalation"
    if "载荷投递" in raw_stage or "payload" in text:
        return "payload_delivery"
    if "影响" in raw_stage or "impact" in text:
        return "impact"
    return "initial_exec"


#: PRD 3.7.4.8.2 / 3.7.5.8.1：报告攻击路径图是五段 kill chain（侦察/投递/提权/渗出/影响）。
#: 与前端报告页 STAGE_ORDER 逐字对齐，改这里就要同步改那边。
KILL_CHAIN_STAGES = ("recon", "delivery", "privilege_escalation", "exfiltration", "impact")

#: 六段归一到五段：载荷投递与初始执行合并为"投递"
_KILL_CHAIN_COLLAPSE = {"payload_delivery": "delivery", "initial_exec": "delivery"}


def kill_chain_stage(raw_stage: str) -> str:
    """把类别 stage 文本归一到报告攻击路径的五段 kill chain。"""
    stage = normalize_stage(raw_stage)
    return _KILL_CHAIN_COLLAPSE.get(stage, stage)


def stage_of_category(category_code: str) -> str:
    """按类别代号取它声明的 kill chain 阶段（五段）；类别缺失时按投递兜底。"""
    category = get_category(str(category_code))
    return kill_chain_stage(category.stage) if category else "delivery"


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