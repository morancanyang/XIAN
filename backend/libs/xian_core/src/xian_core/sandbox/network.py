"""沙箱网络：egress 白名单与蜜标域名映射（PRD 3.1.5.8.1）。

机制保证"从机制上杜绝真实外联"：所有出网请求必须经 egress 代理；白名单外一律
拒绝；外部域名统一映射到平台假域名，请求体命中蜜标即判渗出成功。
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from ..errors import EgressBlocked as SandboxNetworkError

DEFAULT_ALLOWLIST: tuple[str, ...] = (
    "api.xian-internal.example",
    "llm.xian-internal.example",
    "registry.xian-internal.example",
)

FAKE_DOMAIN_SUFFIX = ".xian-sandbox.invalid"
DOMAIN_PATTERN = re.compile(r"^(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$", re.I)


@dataclass(slots=True)
class EgressDecision:
    allowed: bool
    reason: str = ""
    mapped_domain: str = ""
    canary_hit: bool = False


@dataclass(slots=True)
class EgressProxy:
    allowlist: tuple[str, ...] = DEFAULT_ALLOWLIST
    canary_values: tuple[str, ...] = ()
    blocked: list[dict] = field(default_factory=list)
    logged: list[dict] = field(default_factory=list)

    def map_domain(self, domain: str) -> str:
        """外部域名统一映射到平台假域名（*.xian-sandbox.invalid）。"""
        return domain.strip().lower().replace(".", "-") + FAKE_DOMAIN_SUFFIX

    def is_allowed(self, domain: str) -> bool:
        host = domain.strip().lower()
        return any(host == entry or host.endswith("." + entry) for entry in self.allowlist)

    def scan_body(self, body: str) -> bool:
        return any(value and value in body for value in self.canary_values)

    def intercept(self, *, domain: str, body: str = "", method: str = "POST") -> EgressDecision:
        """代理主入口：域名映射 → 白名单判定 → 蜜标扫描。"""
        mapped = self.map_domain(domain)
        if not self.is_allowed(domain):
            decision = EgressDecision(allowed=False, reason=f"域名 {domain} 不在白名单，已拒绝", mapped_domain=mapped)
            self.blocked.append({"domain": domain, "mapped": mapped, "method": method, "reason": decision.reason})
            return decision
        canary_hit = self.scan_body(body)
        decision = EgressDecision(allowed=True, reason="白名单内放行", mapped_domain=mapped, canary_hit=canary_hit)
        self.logged.append(
            {
                "domain": domain,
                "mapped_domain": mapped,
                "method": method,
                "canary_hit": canary_hit,
                "body_hash": _hash(body),
            }
        )
        return decision

    def require_allowed(self, *, domain: str, body: str = "", method: str = "POST") -> EgressDecision:
        decision = self.intercept(domain=domain, body=body, method=method)
        if not decision.allowed:
            raise SandboxNetworkError(decision.reason)
        return decision


def _hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def assert_no_real_credential(text: str) -> None:
    """演练前扫描：发现疑似真实凭证立即阻断（PRD 3.1.5.6）。"""
    suspicious = (
        "AKIA",
        "sk-proj-",
        "ghp_",
        "xoxb-",
        "-----BEGIN PRIVATE KEY-----",
        "AIza",
    )
    for token in suspicious:
        if token in text:
            raise SandboxNetworkError(f"检测到疑似真实凭证片段 {token}，演练已被安全策略阻止")


def validate_allowlist(entries: Iterable[str]) -> list[str]:
    out: list[str] = []
    for entry in entries:
        host = entry.strip().lower()
        if not DOMAIN_PATTERN.match(host):
            raise SandboxNetworkError(f"白名单条目 {entry} 不是合法域名")
        out.append(host)
    return out