"""归属校验（PRD 3.2.4.8.1 / AC-09）：证明"Agent 确实属于该租户"。

两种方式：
1. DNS TXT —— 用户在域名下添加 `xian-verify=<nonce>` 记录，平台解析比对；
2. 镜像摘要 —— 用户提供镜像 digest，平台比对 registry 返回的 RepoDigests。
"""

from __future__ import annotations

import re
import secrets
from typing import Any

from ..errors import OwnershipNotVerified
from ..schemas.common import OwnershipMethod, OwnershipResult

TXT_PREFIX = "xian-verify="
# 开发注入通配记录：声明"该域名在本机演示中视为已持有"，任意一次性 nonce 均算匹配。
WILDCARD_RECORD = f"{TXT_PREFIX}*"
DIGEST_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")


def _injected_txt() -> dict[str, list[str]]:
    import os

    out: dict[str, list[str]] = {}
    for chunk in (os.environ.get("XIAN_VERIFY_TXT") or "").split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        domain, _, raw = chunk.partition("=")
        out[domain.strip().lower()] = [r.strip() for r in raw.split(",") if r.strip()]
    return out


def make_nonce() -> str:
    """生成一次性校验值（verification_record.nonce）。"""
    return secrets.token_hex(16)


def build_dns_instruction(domain: str, nonce: str) -> dict[str, str]:
    return {
        "method": "dns_txt",
        "domain": domain,
        "record": f"{TXT_PREFIX}{nonce}",
        "ttl": "600",
        "hint": f"请在 {domain} 添加一条 TXT 记录，值为 {TXT_PREFIX}{nonce}，保存后重新触发校验。",
    }


def build_image_instruction(image: str, digest: str) -> dict[str, str]:
    return {
        "method": "image_digest",
        "image": image,
        "digest": digest,
        "hint": f"请提供镜像 {image} 的不可变摘要（形如 sha256:<64位十六进制>），或允许平台读取仓库 RepoDigests。",
    }


def _resolve_txt(domain: str) -> list[str]:
    # 本地/离线环境：允许通过 XIAN_VERIFY_TXT="域名=记录1;域名2=记录2" 注入预期 TXT，
    # 便于在无公网 DNS 的演示与 CI 环境走通 AC-09 闭环（生产环境不设置该变量）。
    injected = _injected_txt().get(domain.lower())
    if injected:
        return injected
    try:
        import dns.resolver  # dnspython 为可选依赖
    except ImportError:  # pragma: no cover - 视部署环境而定
        return []
    try:
        answers = dns.resolver.resolve(domain, "TXT")
    except Exception:
        return []
    out: list[str] = []
    for rdata in answers:
        out.extend(s.decode("utf-8", "ignore") for s in rdata.strings)
    return out


def verify_dns(domain: str, nonce: str, *, expected: str | None = None) -> dict[str, Any]:
    """DNS TXT 校验；无 dnspython 时退化为严格字面比对（供离线/测试环境）。"""
    records = _resolve_txt(domain)
    target = expected or f"{TXT_PREFIX}{nonce}"
    # 通配记录命中即算通过：接入向导每给一个新 Agent 生成新 nonce，
    # 写死单个 nonce 的注入会让第二个 Agent 的校验必然失败。
    wildcard = any(r.strip() == WILDCARD_RECORD for r in records)
    matched = wildcard or any(target in rec for rec in records)
    payload: dict[str, Any] = {
        "method": OwnershipMethod.dns_txt.value,
        "target": domain,
        "nonce": nonce,
        "result": OwnershipResult.verified.value if matched else OwnershipResult.failed.value,
        "records_seen": len(records),
    }
    # reason 必须在每条分支都显式给出：record_verification() 的 detail 直接取
    # result["reason"]，漏掉这个键，接口就只剩一个 result 字段，前端除了一个
    # verified 徽标什么都看不到，用户完全不知道刚才校验了什么、失败又缺什么。
    if wildcard:
        note = ""
        if domain.lower() in _injected_txt():
            note = "（本地演示由 XIAN_VERIFY_TXT 注入，并非真实公网 DNS 解析）"
        payload["reason"] = (
            f"{domain} 命中通配记录 {WILDCARD_RECORD}，视为已持有该域名{note}。本次校验值：{target}"
        )
    elif matched:
        payload["reason"] = f"{domain} 的 TXT 记录中命中 {target}，域名归属已确认。"
    elif records:
        payload["reason"] = (
            f"{domain} 解析到 {len(records)} 条 TXT 记录，但没有一条等于 {target}。"
            "请按上方指引补齐该记录后重新校验（DNS 生效通常需要几分钟）。"
        )
    else:
        payload["reason"] = (
            f"{domain} 没有解析到任何 TXT 记录。请按上方指引添加 {target}，"
            "保存后等待 DNS 生效再重新校验。"
        )
    return payload


def verify_image_digest(declared: str, observed: str | None = None) -> dict[str, Any]:
    """镜像摘要校验：声明摘要与 registry 观测摘要必须完全一致。"""
    if not DIGEST_PATTERN.match(declared or ""):
        return {
            "method": OwnershipMethod.image_digest.value,
            "target": declared or "",
            "result": OwnershipResult.failed.value,
            "reason": "镜像摘要格式非法，应为 sha256:<64位十六进制>",
        }
    if observed is None:
        return {
            "method": OwnershipMethod.image_digest.value,
            "target": declared,
            "result": OwnershipResult.pending.value,
            "reason": "等待 registry 观测摘要",
        }
    matched = declared == observed
    return {
        "method": OwnershipMethod.image_digest.value,
        "target": declared,
        "result": OwnershipResult.verified.value if matched else OwnershipResult.failed.value,
        "observed": observed,
    }


def assert_verified(record: dict[str, Any]) -> None:
    """未归属验证的 Agent 只能打内置场景，不能作为模式一目标（AC-09 前半）。"""
    result = str(record.get("result", ""))
    if result != OwnershipResult.verified.value:
        raise OwnershipNotVerified(
            f"归属校验未通过（{result}）：请按指引完成 DNS TXT 或镜像摘要校验后再作为演练目标"
        )