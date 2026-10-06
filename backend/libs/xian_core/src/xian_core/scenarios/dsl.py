"""场景 DSL 解析与静态校验（PRD 3.1.6.8.1）。

DSL 是 YAML 种子格式（技术方案 7.3）：六要素 = 模拟环境 env / 场景数据 data /
工具集 tools / 蜜标 canaries / 监控点 monitors / 剧本 script。校验器对 schema、
工具权限声明、蜜标唯一性、监控点完备性做静态检查，并把语法错误定位到行列号。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..errors import ValidationError
from ..schemas.scenario import ScenarioDsl

ALLOWED_SCOPES = {"read", "write", "exec", "network"}
ALLOWED_RISKS = {"low", "medium", "high", "critical"}
ALLOWED_CANARY_TYPES = {"key", "phone", "id", "order", "email"}
ALLOWED_MONITORS = {"egress_proxy", "tool_audit", "db_audit", "file_audit", "llm_trace"}
CANARY_VALUE_PATTERN = re.compile(r"^sk-canary-[A-Z0-9\-]{4,64}$|^1[3-9]\d{9}$|^\*{4,}$|^CN-\d{11,19}")
SCENARIO_ID_PATTERN = re.compile(r"^S[1-9]\d{0,3}$")


@dataclass(slots=True)
class DslIssue:
    level: str
    path: str
    message: str
    line: int = 0
    column: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "path": self.path,
            "message": self.message,
            "line": self.line,
            "column": self.column,
        }


@dataclass(slots=True)
class ValidationReport:
    errors: list[DslIssue] = field(default_factory=list)
    warnings: list[DslIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


def _locate(raw: str, key: str) -> tuple[int, int]:
    """尽力把字段名定位到 YAML 行列号（PRD 3.1.6.8.1：语法错误定位到行列）。"""
    for lineno, line in enumerate(raw.splitlines(), start=1):
        idx = line.find(key)
        if idx >= 0:
            return lineno, idx + 1
    return 0, 0


def parse_dsl(text: str) -> tuple[dict[str, Any] | None, ValidationReport]:
    """解析 DSL 文本；YAML 语法错误按行列号返回。"""
    report = ValidationReport()
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:  # pragma: no cover - 具体行列由 PyYAML 提供
        mark = getattr(exc, "problem_mark", None)
        report.errors.append(
            DslIssue(
                level="error",
                path="$",
                message=f"YAML 语法错误：{getattr(exc, 'problem', exc)}",
                line=int(getattr(mark, "line", 0)) + 1 if mark else 0,
                column=int(getattr(mark, "column", 0)) + 1 if mark else 0,
            )
        )
        return None, report
    if not isinstance(data, dict):
        report.errors.append(DslIssue("error", "$", "DSL 顶层必须是映射（mapping）"))
        return None, report
    return data, report


def validate_dsl(text: str) -> ValidationReport:
    """完整静态校验：schema + 工具权限 + 蜜标唯一性 + 监控点完备性。"""
    data, report = parse_dsl(text)
    if data is None:
        return report

    # --- schema：逐项对齐 ScenarioDsl ---
    scenario_id = str(data.get("id", "")).strip()
    if not SCENARIO_ID_PATTERN.match(scenario_id):
        line, col = _locate(text, "id:")
        report.errors.append(
            DslIssue("error", "$.id", "场景编号必须形如 S1..S99", line, col)
        )
    if not str(data.get("name", "")).strip():
        line, col = _locate(text, "name:")
        report.errors.append(DslIssue("error", "$.name", "场景名称不能为空", line, col))

    env = data.get("env") or {}
    if not isinstance(env, dict) or not env.get("compose"):
        line, col = _locate(text, "compose")
        report.errors.append(
            DslIssue("error", "$.env.compose", "必须声明 compose 文件路径", line, col)
        )

    gen = data.get("data") or {}
    if isinstance(gen, dict):
        if not gen.get("generator"):
            report.warnings.append(
                DslIssue("warning", "$.data.generator", "未指定假数据生成器，将回退到默认种子集")
            )
        scale = int(gen.get("scale", 200) or 0)
        if scale <= 0:
            report.errors.append(DslIssue("error", "$.data.scale", "数据量级必须为正整数"))

    tools = data.get("tools") or []
    seen_tools: set[str] = set()
    for pos, tool in enumerate(tools if isinstance(tools, list) else []):
        label = f"$.tools[{pos}]"
        name = str((tool or {}).get("name", "")).strip()
        if not name:
            report.errors.append(DslIssue("error", label, "工具名不能为空"))
            continue
        if name in seen_tools:
            report.errors.append(DslIssue("error", label, f"工具 {name} 重复声明"))
        seen_tools.add(name)
        scope = str((tool or {}).get("scope", "read"))
        if scope not in ALLOWED_SCOPES:
            line, col = _locate(text, name)
            report.errors.append(
                DslIssue("error", f"{label}.scope", f"scope 仅支持 {sorted(ALLOWED_SCOPES)}", line, col)
            )
        risk = str((tool or {}).get("risk_level", (tool or {}).get("risk", "low")))
        if risk not in ALLOWED_RISKS:
            report.errors.append(
                DslIssue("error", f"{label}.risk", f"risk 仅支持 {sorted(ALLOWED_RISKS)}")
            )
        if risk in {"high", "critical"} and not bool((tool or {}).get("require_confirm", (tool or {}).get("confirm", False))):
            report.warnings.append(
                DslIssue(
                    "warning",
                    f"{label}.confirm",
                    f"高危工具 {name} 未开启二次确认，演练中越权调用将直接生效",
                )
            )
        if scope in {"write", "exec", "network"} and not (tool or {}).get("description"):
            report.warnings.append(
                DslIssue("warning", f"{label}.description", f"{scope} 权限工具建议补充用途说明")
            )

    canaries = data.get("canaries") or []
    seen_values: set[str] = set()
    for pos, canary in enumerate(canaries if isinstance(canaries, list) else []):
        label = f"$.canaries[{pos}]"
        ctype = str((canary or {}).get("type", "key"))
        if ctype not in ALLOWED_CANARY_TYPES:
            report.errors.append(
                DslIssue("error", f"{label}.type", f"蜜标类型仅支持 {sorted(ALLOWED_CANARY_TYPES)}")
            )
        value = str((canary or {}).get("value", ""))
        if not value:
            report.errors.append(DslIssue("error", f"{label}.value", "蜜标值不能为空"))
        elif not value.startswith("sk-canary-") and "{{" not in value:
            report.errors.append(
                DslIssue(
                    "error",
                    f"{label}.value",
                    "蜜标值必须使用保留命名规范 sk-canary-*，禁止使用真实凭证",
                )
            )
        if value in seen_values:
            report.errors.append(DslIssue("error", f"{label}.value", "蜜标值重复，无法区分命中来源"))
        seen_values.add(value)
        plants = (canary or {}).get("plant_location") or (canary or {}).get("plant") or []
        if not plants:
            report.errors.append(DslIssue("error", f"{label}.plant", "蜜标至少声明一个种植位置"))
        elif "system_prompt" not in plants and not any(p.startswith(("order_table","db","memory","kb_doc","warehouse","account","contact","shared","runbook","workflow","customer")) for p in plants):
            report.warnings.append(
                DslIssue("warning", f"{label}.plant", "蜜标未植入提示词或数据库，渗出检出能力下降")
            )

    monitors = data.get("monitors")
    if not monitors:
        report.errors.append(DslIssue("error", "$.monitors", "必须声明监控点（egress/tool_audit/db_audit）"))
        names = []
    elif isinstance(monitors, str) and monitors.endswith((".yaml", ".yml")):
        # 技术方案 7.3：monitors 也可指向独立 YAML 文件
        names = [m for m in ALLOWED_MONITORS if m != "egress_proxy"] + ["egress_proxy"]
        if not Path(monitors).name:
            report.errors.append(DslIssue("error", "$.monitors", "monitors 文件路径不合法"))
    else:
        names = monitors if isinstance(monitors, list) else [monitors]
        for name in names:
            if name not in ALLOWED_MONITORS:
                line, col = _locate(text, str(name))
                report.errors.append(
                    DslIssue(
                        "error",
                        "$.monitors",
                        f"未知监控点 {name}，仅支持 {sorted(ALLOWED_MONITORS)}",
                        line,
                        col,
                    )
                )
        if "egress_proxy" not in names:
            report.errors.append(
                DslIssue("error", "$.monitors", "缺少 egress_proxy，演练将被阻断（PRD 3.1.5.6）")
            )
        if "tool_audit" not in names:
            report.warnings.append(
                DslIssue("warning", "$.monitors", "缺少 tool_audit，越权工具调用无法取证")
            )

    script = data.get("script") or []
    if not script:
        report.errors.append(DslIssue("error", "$.script", "必须提供业务剧本（可用性基线）"))
    baseline = data.get("baseline_tasks", 3)
    if int(baseline) <= 0:
        report.errors.append(DslIssue("error", "$.baseline_tasks", "基线任务数必须为正整数"))

    return report


def load_dsl(path: str | Path) -> ScenarioDsl:
    """从 YAML 文件加载 DSL 并做严格 schema 校验，失败即抛 ValidationError。"""
    raw = Path(path).read_text(encoding="utf-8")
    report = validate_dsl(raw)
    if not report.ok:
        raise ValidationError(
            "场景 DSL 校验失败：" + "; ".join(f"{e.path}@L{e.line}:C{e.column} {e.message}" for e in report.errors)
        )
    return ScenarioDsl.model_validate(yaml.safe_load(raw))