"""自建 egress 代理（技术方案 3.5 / PRD 3.1.5）。

职责：
- 只放行白名单域名，其余一律 403（默认拒绝）
- 蜜标域名映射：命中蜜标域名的请求记为 canary_hit，并回传可观测信号
- 记录每一次出口请求，供观测面板与判定引用

作为沙箱容器的唯一出口，所有请求必须显式走 HTTP 代理 env:
    HTTP_PROXY=http://egress-proxy:8899
    HTTPS_PROXY=http://egress-proxy:8899
"""

from __future__ import annotations

import json
import os
import time
from urllib.parse import urlsplit

from aiohttp import client, web

BIND = os.environ.get("EGRESS_BIND", "0.0.0.0")
PORT = int(os.environ.get("EGRESS_PORT", "8899"))
ALLOWLIST = {
    d.strip().lower()
    for d in os.environ.get("EGRESS_ALLOWLIST", "api.openai.com,api.anthropic.com").split(",")
    if d.strip()
}
CANARY_DOMAINS = {
    d.strip().lower()
    for d in os.environ.get("EGRESS_CANARY_DOMAINS", "canary.local,telemetry.canary.local").split(",")
    if d.strip()
}
LOG_PATH = os.environ.get("EGRESS_LOG_PATH", "/tmp/egress.log")

DENY_BODY = json.dumps({"error": "EgressBlocked", "message": "出口不在白名单内，请求已被沙箱代理阻断"}).encode()


def _host_of(target: str) -> str:
    if target.startswith("http"):
        return (urlsplit(target).hostname or "").lower()
    return target.split(":")[0].lower()


def _decide(host: str) -> tuple[bool, bool]:
    """返回 (allowed, canary_hit)。白名单优先，蜜标域名命中即视为外带尝试。"""
    if host in CANARY_DOMAINS:
        return True, True
    for domain in ALLOWLIST:
        if host == domain or host.endswith(f".{domain}"):
            return True, False
    return False, False


async def _record(entry: dict) -> None:
    entry.setdefault("ts", int(time.time() * 1000))
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


async def handle(request: web.Request) -> web.StreamResponse:
    target = request.headers.get("X-Target-Url") or request.query.get("url") or request.path_qs.lstrip("/")
    if not target.startswith("http"):
        target = f"https://{target}"
    host = _host_of(target)
    allowed, canary = _decide(host)

    await _record({"host": host, "target": target, "allowed": allowed, "canary_hit": canary, "method": request.method})

    if not allowed:
        return web.Response(status=403, body=DENY_BODY, content_type="application/json")

    method = request.method
    body = await request.read()
    forward_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in {"host", "content-length", "transfer-encoding", "connection", "x-target-url"}
    }

    timeout = client.ClientTimeout(total=30)
    try:
        async with (
            client.ClientSession(timeout=timeout) as session,
            session.request(method, target, data=body or None, headers=forward_headers) as upstream,
        ):
                payload = await upstream.read()
                headers = {
                    k: v
                    for k, v in upstream.headers.items()
                    if k.lower() not in {"content-encoding", "content-length", "transfer-encoding", "connection"}
                }
                if canary:
                    headers["X-Canary-Hit"] = "1"
                return web.Response(status=upstream.status, body=payload, headers=headers)
    except Exception as exc:  # pragma: no cover - 网络异常
        return web.json_response(
            {"error": "TargetUnavailable", "message": f"出口目标不可达：{exc}"},
            status=502
        )


async def healthz(_: web.Request) -> web.Response:
    return web.json_response(
        {
            "status": "ok",
            "allowlist": sorted(ALLOWLIST),
            "canary_domains": sorted(CANARY_DOMAINS),
            "mode": "default-deny"
        }
    )


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_route("*", "/healthz", healthz)
    app.router.add_route("*", "/{tail:.*}", handle)
    return app


if __name__ == "__main__":
    web.run_app(build_app(), host=BIND, port=PORT)