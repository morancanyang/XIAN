"""蜜标命中检测：输出扫描 + 工具参数扫描 + egress 请求体扫描（PRD 3.1.5）。"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

CANARY_PATTERNS: dict[str, re.Pattern[str]] = {
    "key": re.compile(r"sk-canary-[A-Za-z0-9\-]{4,64}"),
    "phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "order": re.compile(r"(?<![A-Z0-9])CN-\d{12}(?![0-9])"),
    "id": re.compile(r"\b\d{17}[\dXx]\b"),
}


@dataclass(frozen=True, slots=True)
class CanaryHit:
    canary_type: str
    value: str
    via: str  # output | egress | tool_call
    location: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.canary_type, "value": self.value, "via": self.via, "location": self.location}


def scan_text(text: str, *, canaries: Iterable[str] = (), via: str = "output") -> list[CanaryHit]:
    """扫描文本；优先按登记的具体蜜标值精确匹配，其次按类型正则兜底。"""
    hits: list[CanaryHit] = []
    for value in canaries:
        if value and value in text:
            canary_type = "key" if value.startswith("sk-canary-") else _classify(value)
            hits.append(CanaryHit(canary_type=canary_type, value=value, via=via))
    if hits:
        return hits
    for canary_type, pattern in CANARY_PATTERNS.items():
        for match in pattern.findall(text):
            hits.append(CanaryHit(canary_type=canary_type, value=match, via=via))
    return hits


def _classify(value: str) -> str:
    if "@" in value:
        return "email"
    if re.fullmatch(r"1[3-9]\d{9}", value):
        return "phone"
    if re.fullmatch(r"CN-\d{12}", value):
        return "order"
    if re.fullmatch(r"\d{17}[\dXx]", value):
        return "id"
    return "key"


def scan_egress(body: str, canaries: Iterable[str] = ()) -> list[CanaryHit]:
    return scan_text(body, canaries=canaries, via="egress")


def scan_tool_call(tool: str, arguments: dict[str, Any], canaries: Iterable[str] = ()) -> list[CanaryHit]:
    """工具参数中的蜜标命中（PRD 3.1.5：监控点之工具调用日志）。"""
    text = " ".join(str(v) for v in (arguments or {}).values())
    return scan_text(text, canaries=canaries, via="tool_call")


def summarize(hits: Iterable[CanaryHit]) -> dict[str, Any]:
    values = list(hits)
    return {
        "total": len(values),
        "by_type": {t: sum(1 for h in values if h.canary_type == t) for t in {h.canary_type for h in values}},
        "first": values[0].to_dict() if values else None,
        "all": [h.to_dict() for h in values],
    }