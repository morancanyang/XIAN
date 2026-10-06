"""连通性与健康探测（PRD 3.2.4.8.2）：3 条无害探测 + 首响延迟 + trace 采样。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PROBES = (
    "你好，请做一次自我介绍，只说明你的职责范围。",
    "请列出你可以调用的工具名称（无需参数）。",
    "这是一次连通性测试，请回复 pong。",
)


@dataclass(slots=True)
class ProbeResult:
    prompt: str
    ok: bool
    latency_ms: int = 0
    reply: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "ok": self.ok,
            "latency_ms": self.latency_ms,
            "reply": self.reply[:200],
            "error": self.error,
        }


@dataclass(slots=True)
class HealthReport:
    result: str
    latency_ms: int
    probes: list[ProbeResult] = field(default_factory=list)
    trace_sample: list[dict[str, Any]] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.result == "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "latency_ms": self.latency_ms,
            "probes": [p.to_dict() for p in self.probes],
            "trace_sample": self.trace_sample,
            "hints": self.hints,
        }


TROUBLESHOOT: dict[str, str] = {
    "timeout": "端点响应超时：请检查网关超时设置与网络策略，或提高 probe_timeout。",
    "auth": "鉴权失败（401/403）：请确认接入凭证 scope 与过期时间。",
    "rate_limited": "触发限流（429）：请降低并发或申请演练专用配额。",
    "server_error": "目标返回 5xx：请确认 Agent 服务健康，或稍后重试。",
    "sensitive": "探测响应中疑似含真实敏感信息，演练已被阻断，请不要在测试环境使用真实凭证。",
}


def classify_failure(status: int | None, message: str = "") -> str:
    if "timed out" in message.lower() or status is None:
        return "timeout"
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "rate_limited"
    if status and status >= 500:
        return "server_error"
    return "server_error"


def build_report(probes: list[ProbeResult]) -> HealthReport:
    """汇总探测结果；任一无响应即整体失败，并给出对应排障建议。"""
    ok = all(p.ok for p in probes) and bool(probes)
    latency = max((p.latency_ms for p in probes), default=0)
    hints: list[str] = []
    if not probes:
        hints.append(TROUBLESHOOT["server_error"])
    for p in probes:
        if not p.ok:
            hints.append(TROUBLESHOOT.get(classify_failure(None, p.error), TROUBLESHOOT["server_error"]))
    return HealthReport(
        result="ok" if ok else "error",
        latency_ms=latency,
        probes=probes,
        trace_sample=[
            {"seq": i, "role": "assistant", "latency_ms": p.latency_ms} for i, p in enumerate(probes, start=1)
        ],
        hints=list(dict.fromkeys(hints)),
    )