"""场景模板目录与匹配推荐（PRD 3.1.4 / 3.1.4.8.1）。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..schemas.scenario import ScenarioDsl
from .dsl import validate_dsl

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


@dataclass(frozen=True, slots=True)
class ScenarioTemplate:
    dsl: ScenarioDsl
    source: Path

    @property
    def code(self) -> str:
        return self.dsl.id

    @property
    def name(self) -> str:
        return self.dsl.name

    @property
    def agent_form(self) -> str:
        return str(self.dsl.agent_form)

    @property
    def exam_tags(self) -> list[str]:
        return list(self.dsl.exam_tags)

    @property
    def tool_names(self) -> list[str]:
        return [t.name for t in self.dsl.tools]

    def to_dict(self) -> dict[str, Any]:
        payload = self.dsl.model_dump(mode="json")
        payload["agent_form"] = self.agent_form
        payload["exam_tags"] = self.exam_tags
        payload["tool_names"] = self.tool_names
        return payload


@lru_cache(maxsize=1)
def load_templates() -> tuple[ScenarioTemplate, ...]:
    """加载全部内置场景模板；DSL 校验失败即视为内容资产缺陷，直接抛错。"""
    out: list[ScenarioTemplate] = []
    for path in sorted(TEMPLATE_DIR.glob("S*/scenario.yaml")):
        raw = path.read_text(encoding="utf-8")
        report = validate_dsl(raw)
        if not report.ok:
            detail = "; ".join(f"{e.path}@L{e.line}:C{e.column} {e.message}" for e in report.errors)
            raise ValueError(f"场景模板 {path.parent.name} 校验失败：{detail}")
        out.append(ScenarioTemplate(dsl=ScenarioDsl.model_validate(yaml.safe_load(raw)), source=path))
    if not out:
        raise RuntimeError(f"未找到任何场景模板：{TEMPLATE_DIR}")
    return tuple(out)


def all_templates() -> list[ScenarioTemplate]:
    return list(load_templates())


def get_template(code: str) -> ScenarioTemplate | None:
    for template in load_templates():
        if template.code == code:
            return template
    return None


def require_template(code: str) -> ScenarioTemplate:
    template = get_template(code)
    if template is None:
        raise KeyError(f"场景 {code} 不存在")
    return template


def filter_templates(
    *,
    difficulty: str | None = None,
    tag: str | None = None,
    agent_form: str | None = None,
) -> list[ScenarioTemplate]:
    out: list[ScenarioTemplate] = []
    for template in load_templates():
        if difficulty and str(template.dsl.difficulty) != difficulty:
            continue
        if tag and tag not in template.exam_tags:
            continue
        if agent_form and agent_form not in template.agent_form:
            continue
        out.append(template)
    return out


def _norm(text: str) -> str:
    return text.strip().lower().replace("-", "_").replace(" ", "_")


def match_score(template: ScenarioTemplate, agent_tools: Iterable[str]) -> tuple[float, list[str], list[str]]:
    """规则匹配：工具重合度 × 考点覆盖度（PRD 3.1.4.8.1）。"""
    declared = {_norm(t) for t in agent_tools if t}
    available = {_norm(t) for t in template.tool_names}
    if not declared:
        return 0.0, [], ["Agent 未声明工具清单，建议先完成侦察"]
    overlap = sorted(declared & available)
    coverage = len(overlap) / max(len(available), 1)
    return round(coverage, 4), overlap, [f"工具重合 {len(overlap)}/{len(available)}"]


def recommend(agent_tools: Iterable[str], *, has_memory: bool = False, has_rag: bool = False, top: int = 3) -> list[dict[str, Any]]:
    """场景匹配推荐 Top-N（PRD 3.1.4.8.1）。"""
    scored: list[tuple[float, ScenarioTemplate, list[str], list[str]]] = []
    for template in load_templates():
        score, overlap, reasons = match_score(template, agent_tools)
        if has_memory and "记忆" in "".join(template.exam_tags):
            score = min(1.0, score + 0.15)
            reasons.append("Agent 具备长期记忆，记忆类考点加权")
        if has_rag and "RAG" in template.exam_tags:
            score = min(1.0, score + 0.15)
            reasons.append("Agent 使用 RAG，RAG 类考点加权")
        if template.code == "S1" and not overlap:
            score = max(score, 0.3)
            reasons.append("通用推荐：客服场景覆盖面最广")
        scored.append((score, template, overlap, reasons))
    scored.sort(key=lambda item: (-item[0], item[1].code))
    return [
        {
            "scenario_id": template.code,
            "scenario_name": template.name,
            "match_score": round(score, 4),
            "matched_tools": overlap,
            "reasons": reasons,
            "difficulty": str(template.dsl.difficulty),
        }
        for score, template, overlap, reasons in scored[:top]
    ]