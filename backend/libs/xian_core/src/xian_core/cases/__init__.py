"""攻击用例库：加载、渲染、贡献评审、导出管控（PRD 3.5.5）。"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..errors import ExportForbidden, ValidationError
from ..schemas.attack import AttackCaseCreate, AttackCaseOut

SEED_DIR = Path(__file__).resolve().parent / "seed"

VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


@dataclass(slots=True)
class AttackCaseAsset:
    case_id: str
    category_code: str
    title: str
    payload_template: str
    variables: list[str] = field(default_factory=list)
    scenario_tags: list[str] = field(default_factory=list)
    difficulty: str = "medium"
    severity: str = "high"
    success_criteria: dict[str, Any] = field(default_factory=dict)
    judge_prompt: str = ""
    success_rate: float = 0.0
    status: str = "published"
    version: int = 1
    contributor: str = "platform"

    @property
    def id(self) -> str:
        return self.case_id

    def to_out(self) -> AttackCaseOut:
        return AttackCaseOut(
            id=self.case_id,
            category_id=self.category_code,
            title=self.title,
            payload_template=self.payload_template,
            variables=list(self.variables),
            scenario_tags=list(self.scenario_tags),
            difficulty=self.difficulty,  # type: ignore[arg-type]
            severity=self.severity,  # type: ignore[arg-type]
            success_criteria=dict(self.success_criteria),
            judge_prompt=self.judge_prompt,
            success_rate=self.success_rate,
            status=self.status,
            version=self.version,
            contributor=self.contributor,
        )


@lru_cache(maxsize=1)
def load_seed_cases() -> tuple[AttackCaseAsset, ...]:
    assets: list[AttackCaseAsset] = []
    for path in sorted(SEED_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for case in raw.get("cases", []):
            assets.append(
                AttackCaseAsset(
                    case_id=case["id"],
                    category_code=case.get("category", raw.get("category", "")),
                    title=case["title"],
                    payload_template=case["payload_template"],
                    variables=list(case.get("variables", [])),
                    scenario_tags=list(case.get("scenario_tags", [])),
                    difficulty=case.get("difficulty", "medium"),
                    severity=case.get("severity", "high"),
                    success_criteria=dict(case.get("success_criteria", {})),
                    judge_prompt=case.get("judge_prompt", ""),
                    success_rate=float(case.get("success_rate", 0.0)),
                    status=case.get("status", "published"),
                    version=int(case.get("version", 1)),
                    contributor=case.get("contributor", "platform"),
                )
            )
    return tuple(assets)


def all_cases() -> list[AttackCaseAsset]:
    return list(load_seed_cases())


def cases_by_category(code: str) -> list[AttackCaseAsset]:
    return [c for c in load_seed_cases() if c.category_code == code]


def get_case(case_id: str) -> AttackCaseAsset | None:
    for case in load_seed_cases():
        if case.case_id == case_id:
            return case
    return None


def find_variables(template: str) -> list[str]:
    """提取模板中的 {{变量}} 占位符（去重、保序）。"""
    seen: dict[str, None] = {}
    for match in VAR_PATTERN.finditer(template or ""):
        seen.setdefault(match.group(1), None)
    return list(seen)


def render_payload(template: str, variables: dict[str, str] | None = None) -> str:
    """渲染 {{变量}}；未提供的变量保留占位符（前端会高亮缺失项，PRD 3.4.4.8.1）。"""
    values = variables or {}

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(values.get(key, match.group(0)))

    return VAR_PATTERN.sub(_sub, template or "")


def validate_render(case: AttackCaseAsset, variables: dict[str, str]) -> tuple[bool, list[str]]:
    """变量未填全时禁止发送（PRD 3.4.4.8.1 异常分支）。"""
    missing = [v for v in case.variables if not str(variables.get(v, "")).strip()]
    return (not missing), missing


def select_cases(
    *,
    categories: Iterable[str] | None = None,
    scenario: str | None = None,
    severity: str | None = None,
    difficulty: str | None = None,
    limit: int = 20,
) -> list[AttackCaseAsset]:
    """按类别 / 场景 / 严重度 / 难度筛选，供指挥官方生成战役计划。

    limit 是总预算，按类别轮询均衡分配：每个入选类别先各取一条，再取第二条，直到预算用完。
    之前按种子文件顺序线性截断，排在前面的类别会把预算吃光，靠后的类别一条都拿不到，
    能力雷达上对应的维度会直接消失。"""
    cats = set(categories) if categories else None
    grouped: dict[str, list[AttackCaseAsset]] = {}
    for case in load_seed_cases():
        if case.status != "published":
            continue
        if cats and case.category_code not in cats:
            continue
        if scenario and scenario not in case.scenario_tags:
            continue
        if severity and case.severity != severity:
            continue
        if difficulty and case.difficulty != difficulty:
            continue
        grouped.setdefault(case.category_code, []).append(case)

    out: list[AttackCaseAsset] = []
    queues = [list(items) for items in grouped.values()]
    while queues and len(out) < limit:
        pending: list[list[AttackCaseAsset]] = []
        for queue in queues:
            out.append(queue.pop(0))
            if queue:
                pending.append(queue)
            if len(out) >= limit:
                break
        queues = pending
    return out


# ---------------------------------------------------------------- 贡献评审流水线
PIPELINE_STEPS = ("submitted", "auto_test", "review", "published")


def next_pipeline_status(current: str, passed: bool) -> str:
    """提交 → 自动测试 → 双人评审 → 上线（PRD 3.5.5.8.1）。"""
    order = list(PIPELINE_STEPS)
    if current not in order:
        raise ValidationError(f"未知流水线状态 {current}")
    if not passed:
        return "rejected"
    idx = order.index(current)
    return order[min(idx + 1, len(order) - 1)]


def can_export(case: AttackCaseAsset, *, role: str) -> bool:
    """武器库导出管控（PRD 1.3 / AC-09 后半）：原始载荷默认不可导出。"""
    if role in ("admin",):
        return True
    if case.status != "published":
        return False
    return False


def assert_export_allowed(case: AttackCaseAsset, *, role: str) -> None:
    if not can_export(case, role=role):
        raise ExportForbidden(f"用例 {case.case_id} 的原始载荷禁止导出（角色 {role} 无权限）")


def to_create_payload(case: AttackCaseAsset) -> AttackCaseCreate:
    return AttackCaseCreate(
        id=case.case_id,
        category_id=case.category_code,
        title=case.title,
        payload_template=case.payload_template,
        variables=list(case.variables),
        scenario_tags=list(case.scenario_tags),
        difficulty=case.difficulty,  # type: ignore[arg-type]
        severity=case.severity,  # type: ignore[arg-type]
        success_criteria=dict(case.success_criteria),
        judge_prompt=case.judge_prompt,
        success_rate=case.success_rate,
        status=case.status,
        version=case.version,
        contributor=case.contributor,
    )