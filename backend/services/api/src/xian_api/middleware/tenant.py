"""租户隔离与审计中间件（PRD 3.9.4 / 3.9.5）。"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import ClassVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from xian_core.bus import make_event
from xian_core.contracts import WsEnvelope


class TenantContextMiddleware(BaseHTTPMiddleware):
    """把 tenant/user/role 注入 request.state，供仓储层强制注入 tenant_id。"""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request.state.tenant_id = request.headers.get("x-tenant-id", "")
        request.state.user_id = request.headers.get("x-user-id", "")
        request.state.role = request.headers.get("x-role", "blue")
        request.state.request_id = uuid.uuid4().hex[:16]
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        response.headers["X-Response-Time-Ms"] = str(int((time.perf_counter() - started) * 1000))
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    """审计：所有写操作落 audit_logs（PRD 3.9.5）。"""

    AUDITED_METHODS: ClassVar[set[str]] = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        if request.method in self.AUDITED_METHODS and request.url.path.startswith("/api"):
            request.state.audit = {
                "action": f"{request.method} {request.url.path}",
                "result": "success" if response.status_code < 400 else "failure",
                "ip": request.client.host if request.client else "",
                "tenant_id": getattr(request.state, "tenant_id", ""),
                "user_id": getattr(request.state, "user_id", ""),
                "request_id": getattr(request.state, "request_id", ""),
            }
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """内存态限流；生产态以 Redis 计数实现（PRD 3.9.5）。"""

    def __init__(self, app, *, limit: int = 120, window_s: int = 60) -> None:
        super().__init__(app)
        self.limit = limit
        self.window = window_s
        self._buckets: dict[str, tuple[float, int]] = {}

    def reset(self) -> None:
        # 桶按 tenant+IP 记在中间件实例上，而 app 是模块级单例、实例跨请求存活。
        # 测试共用同一个 app：不清桶，前面用例耗掉的额度会让后面的用例吃到 429。
        self._buckets.clear()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        key = f"{request.state.tenant_id if hasattr(request.state, 'tenant_id') else 'anon'}:{request.client.host if request.client else 'anon'}"
        now = time.time()
        started, count = self._buckets.get(key, (now, 0))
        if now - started > self.window:
            started, count = now, 0
        count += 1
        self._buckets[key] = (started, count)
        if count > self.limit:
            return Response(
                content='{"detail":"请求过于频繁，请稍后重试"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self.window)},
            )
        return await call_next(request)


def ws_envelope(event: str, payload: dict, *, campaign_id: str | None = None, session_id: str | None = None,
                role: str = "system", message: str = "") -> dict:
    """统一 WS 事件信封（技术方案 6.6）。"""
    return WsEnvelope(
        ts=int(time.time() * 1000), type=event, role=role, message=message,  # type: ignore[arg-type]
        payload=payload, campaign_id=campaign_id, session_id=session_id,
    ).model_dump(mode="json")


def as_bus_event(event: str, payload: dict, *, campaign_id: str | None = None, session_id: str | None = None) -> dict:
    return make_event(event_type=event, payload=payload, campaign_id=campaign_id, session_id=session_id).model_dump(mode="json")