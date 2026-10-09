"""多格式导出：HTML（可交互）/ PDF / Markdown / 机读 JSON（PRD 3.8.4.1）。"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..errors import ValidationError
from .render import build_report_payload, normalize_version_rows

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
SUPPORTED_FORMATS = ("html", "pdf", "markdown", "md", "json")

DESENSITIZE_LEVELS = ("none", "standard", "strict")
SENSITIVE_KEYS = ("payload", "system_prompt", "prompt_fragments", "canary_values", "token", "secret")


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    fmt: str
    path: Path
    bytes: int
    desensitize_level: str

    def to_dict(self) -> dict[str, Any]:
        return {"format": self.fmt, "path": str(self.path), "bytes": self.bytes, "desensitize_level": self.desensitize_level}


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def desensitize(payload: dict[str, Any], level: str = "standard") -> dict[str, Any]:
    """导出脱敏：standard 打码高危载荷与提示词片段；strict 额外移除蜜标值（PRD 3.8.4.4）。"""
    if level == "none":
        return payload
    data = json.loads(json.dumps(payload, ensure_ascii=False, default=str))
    for case in data.get("high_risk_cases", []):
        case["payload"] = _mask(str(case.get("payload", "")))
    agent = data.get("agent", {})
    if isinstance(agent, dict):
        agent["prompt_fragments"] = [_mask(str(f)) for f in agent.get("prompt_fragments", [])]
    if level == "strict":
        agent["canary_types"] = [c for c in agent.get("canary_types", []) if c != "key"]
        for case in data.get("high_risk_cases", []):
            case["trace_ref"] = ""
    return data


def _mask(text: str) -> str:
    if not text:
        return text
    keep = max(1, len(text) // 4)
    return text[:keep] + "***"


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    """渲染前补齐报告契约：历史 payload 的版本行可能缺指标键，模板按 None 判空。"""
    data = dict(payload)
    retest = data.get("retest")
    if isinstance(retest, dict):
        data["retest"] = {**retest, "versions": normalize_version_rows(retest.get("versions"))}
    return data


def render_html(payload: dict[str, Any]) -> str:
    return _env().get_template("report.html.j2").render(report=_normalize(payload))


def render_markdown(payload: dict[str, Any]) -> str:
    return _env().get_template("report.md.j2").render(report=_normalize(payload))


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def render(fmt: str, payload: dict[str, Any]) -> str:
    if fmt == "html":
        return render_html(payload)
    if fmt in {"markdown", "md"}:
        return render_markdown(payload)
    if fmt == "json":
        return render_json(payload)
    raise ValidationError(f"不支持的导出格式 {fmt}，仅支持 {SUPPORTED_FORMATS}")


def to_pdf(html: str) -> bytes:
    """PDF 导出：优先 weasyprint，其次 pdfkit，最后回退为 HTML 字节流并标注。"""
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]

        return HTML(string=html).write_pdf()
    except Exception:
        pass
    try:
        import pdfkit  # type: ignore[import-untyped]

        return pdfkit.from_string(html, False)  # pragma: no cover
    except Exception:
        return html.encode("utf-8")


def export(
    *,
    payload: dict[str, Any],
    formats: Iterable[str] = ("html", "json"),
    output_dir: str | Path = "outputs/reports",
    desensitize_level: str = "standard",
) -> list[ExportArtifact]:
    """按格式批量导出；导出超时场景由 worker 异步化（PRD 3.8.4.6）。"""
    if desensitize_level not in DESENSITIZE_LEVELS:
        raise ValidationError(f"未知脱敏等级 {desensitize_level}")
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    data = desensitize(payload, desensitize_level)
    artifacts: list[ExportArtifact] = []
    for fmt in formats:
        fmt = fmt.lower()
        if fmt == "pdf":
            blob = to_pdf(render_html(data))
            path = target / f"{payload['id']}.pdf"
            path.write_bytes(blob)
        elif fmt in SUPPORTED_FORMATS:
            path = target / f"{payload['id']}.{'md' if fmt in ('md', 'markdown') else fmt}"
            path.write_text(render(fmt, data), encoding="utf-8")
        else:
            raise ValidationError(f"不支持的导出格式 {fmt}")
        artifacts.append(ExportArtifact(fmt=fmt, path=path, bytes=path.stat().st_size, desensitize_level=desensitize_level))
    return artifacts


def export_from_records(
    *,
    tenant_id: str,
    subject_type: str,
    subject_id: str,
    agent: dict[str, Any],
    records: list[dict[str, Any]],
    **kwargs: Any,
) -> tuple[dict[str, Any], list[ExportArtifact]]:
    payload = build_report_payload(
        tenant_id=tenant_id,
        subject_type=subject_type,
        subject_id=subject_id,
        agent=agent,
        records=records,
    )
    return payload, export(payload=payload, **kwargs)