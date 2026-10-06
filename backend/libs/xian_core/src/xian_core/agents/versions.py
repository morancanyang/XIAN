"""Agent 配置版本快照与 diff（PRD 3.2.5.1）。"""

from __future__ import annotations

import difflib
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from ..schemas.agent import AgentVersionCreate, AgentVersionOut


def hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _tool_key(tool: dict[str, Any]) -> str:
    return str(tool.get("name", ""))


def diff_tools(old: Iterable[dict[str, Any]], new: Iterable[dict[str, Any]]) -> dict[str, list[str]]:
    old_map = {_tool_key(t): t for t in old}
    new_map = {_tool_key(t): t for t in new}
    added = [k for k in new_map if k not in old_map]
    removed = [k for k in old_map if k not in new_map]
    changed: list[str] = []
    for key in set(old_map) & set(new_map):
        if _tool_key(old_map[key]) and old_map[key].get("scope") != new_map[key].get("scope"):
            changed.append(key)
    return {"added": sorted(added), "removed": sorted(removed), "scope_changed": sorted(changed)}


def diff_params(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    keys = set(old) | set(new)
    out: dict[str, Any] = {}
    for key in sorted(keys):
        before, after = old.get(key), new.get(key)
        if before != after:
            out[key] = {"before": before, "after": after}
    return out


def text_diff(before: str, after: str, *, context: int = 2) -> str:
    return "\n".join(
        difflib.unified_diff(
            (before or "").splitlines(),
            (after or "").splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
            n=context,
        )
    )


@dataclass(slots=True)
class VersionSnapshot:
    agent_id: str
    prompt: str = ""
    tools: list[dict[str, Any]] = field(default_factory=list)
    model_params: dict[str, Any] = field(default_factory=dict)
    source: str = "manual"
    prompt_hash_override: str = ""

    @property
    def prompt_hash(self) -> str:
        """调用方显式给了 prompt_hash（如手动登记版本）就优先用它，否则按提示词原文哈希。"""
        return self.prompt_hash_override or hash_prompt(self.prompt)

    def to_out(self, *, version_id: str, created_at: Any, diff_summary: dict[str, Any] | None = None) -> AgentVersionOut:
        return AgentVersionOut(
            id=version_id,
            agent_id=self.agent_id,
            prompt_hash=self.prompt_hash,
            tools_snapshot=list(self.tools),
            model_params=dict(self.model_params),
            diff_summary=diff_summary or {},
            source=self.source,
            created_at=created_at,
        )


def diff_versions(previous: VersionSnapshot | None, current: VersionSnapshot) -> dict[str, Any]:
    """版本 diff：提示词文本 diff + 工具集合差异 + 模型参数差异（PRD 3.2.5.1）。"""
    summary: dict[str, Any] = {
        "prompt_changed": False,
        "tools": {"added": [], "removed": [], "scope_changed": []},
        "params": {},
    }
    if previous is None:
        summary["initial"] = True
        return summary
    summary["prompt_changed"] = previous.prompt_hash != current.prompt_hash
    summary["tools"] = diff_tools(previous.tools, current.tools)
    summary["params"] = diff_params(previous.model_params, current.model_params)
    summary["changed"] = bool(
        summary["prompt_changed"] or summary["tools"]["added"] or summary["tools"]["removed"]
        or summary["tools"]["scope_changed"] or summary["params"]
    )
    return summary


def fingerprint_of(snapshot: VersionSnapshot) -> str:
    canonical = json.dumps(
        {"prompt": snapshot.prompt, "tools": snapshot.tools, "params": snapshot.model_params},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def from_create(agent_id: str, payload: AgentVersionCreate, *, prompt: str = "") -> VersionSnapshot:
    return VersionSnapshot(
        agent_id=agent_id,
        prompt=prompt,
        tools=list(payload.tools_snapshot),
        model_params=dict(payload.model_params),
        source=payload.source,
        prompt_hash_override=str(payload.prompt_hash or ""),
    )