"""变更检测：提示词/工具变更后提示或自动触发巡检（PRD 3.8.5.1）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .versions import VersionSnapshot, diff_versions


@dataclass(slots=True)
class ChangeSignal:
    kind: str
    diff_preview: dict[str, Any]
    severity: str = "info"
    auto_trigger_scan: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "diff_preview": self.diff_preview,
            "severity": self.severity,
            "auto_trigger_scan": self.auto_trigger_scan,
        }


def detect(previous: VersionSnapshot | None, current: VersionSnapshot) -> ChangeSignal | None:
    summary = diff_versions(previous, current)
    if summary.get("initial"):
        return None
    if not summary.get("changed"):
        return None
    kinds: list[str] = []
    if summary.get("prompt_changed"):
        kinds.append("prompt")
    tools = summary.get("tools", {})
    if tools.get("added") or tools.get("removed") or tools.get("scope_changed"):
        kinds.append("tools")
    if summary.get("params"):
        kinds.append("model_params")
    # 高危变更：新增 exec/network 权限工具，或移除全部工具（疑似绕过采集）
    high_risk = any(t.get("scope") in {"exec", "network"} for t in current.tools) and tools.get("added")
    return ChangeSignal(
        kind="+".join(kinds) or "config",
        diff_preview=summary,
        severity="high" if high_risk else "medium",
        auto_trigger_scan=high_risk,
    )