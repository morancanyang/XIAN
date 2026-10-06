"""XIAN API 服务入口（技术方案 4.1 接入层）。

职责边界：本服务只做协议适配、鉴权、限流、审计与任务派发；
全部业务规则在 ``xian_core`` 中实现，services/api 不得写业务逻辑。
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from xian_core.bus import bus
from xian_core.schemas.events import Channel
from xian_core.config import get_settings
from xian_core.db.session import dispose_db, init_db
from xian_core.errors import GLOBAL_EXCEPTION_HINTS, XianError

from .middleware.tenant import AuditMiddleware, RateLimitMiddleware, TenantContextMiddleware
from .routers import (
    admin,
    agents,
    campaigns,
    levels,
    llm,
    matrix,
    profile,
    records,
    reports_api,
    scenarios,
    sessions,
)

logger = logging.getLogger("xian.api")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(level=logging.INFO)
    try:
        await init_db()
        logger.info("PostgreSQL chema ready")
    except Exception as exc:  # pragma: no cover - 开发态无库时优雅降级
        logger.warning("数据库初始化跳过（%s），仅提供只读与静态接口", exc)
    bus.connect()
    try:
        yield
    finally:
        await dispose_db()


app = FastAPI(
    title=f"{settings.app_name} API",
    version="1.0.0",
    description="AI Agent 红蓝对抗平台 HTTP API（PRD 3.1~3.9）",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(TenantContextMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware, limit=120, window_s=60)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(XianError)
async def domain_exception_handler(_, exc: XianError) -> JSONResponse:
    """全局异常映射（PRD 2.3.1）：领域异常 → 稳定错误码 + 用户可读提示。"""
    code_map = {
        "ValidationError": 400,
        "NotFoundError": 404,
        "PermissionDenied": 403,
        "QuotaExceeded": 429,
        "OwnershipNotVerified": 403,
        "SandboxEnvFailed": 503,
        "EgressBlocked": 403,
        "BudgetTripped": 402,
        "TargetUnavailable": 502,
        "JudgeDegraded": 503,
        "LLMProviderError": 502,
        "ExportForbidden": 403,
        "CanaryCollision": 409,
    }
    status_code = code_map.get(type(exc).__name__, 400)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": type(exc).__name__,
            "message": str(exc),
            "hint": GLOBAL_EXCEPTION_HINTS.get(type(exc).__name__, ""),
        },
    )


PREFIX = settings.api_prefix
app.include_router(agents.router, prefix=PREFIX)
app.include_router(scenarios.router, prefix=PREFIX)
app.include_router(campaigns.router, prefix=PREFIX)
app.include_router(sessions.router, prefix=PREFIX)
app.include_router(records.router, prefix=PREFIX)
app.include_router(reports_api.router, prefix=PREFIX)
app.include_router(matrix.router, prefix=PREFIX)
app.include_router(levels.router, prefix=PREFIX)
app.include_router(profile.router, prefix=PREFIX)
app.include_router(admin.router, prefix=PREFIX)
app.include_router(llm.router, prefix=PREFIX)

from .routers import auth  # noqa: E402  # app 实例创建后再引入，规避循环导入

app.include_router(auth.router, prefix=PREFIX)


@app.get("/healthz", tags=["ops"])
async def healthz() -> dict:
    from xian_core.llm.gateway import gateway

    return {
        "status": "ok",
        "env": settings.env,
        "bus": bus.enabled,
        "llm": {
            "configured": gateway.transport is not None,
            "offline": gateway.offline,
            "provider": settings.llm.provider or "custom",
        },
    }


@app.get("/readyz", tags=["ops"])
async def readyz() -> dict:
    """就绪探针：数据库可达才算 ready。"""
    try:
        from sqlalchemy import text
        from xian_core.db.session import get_sessionmaker

        maker = get_sessionmaker()
        async with maker() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:  # pragma: no cover
        return JSONResponse(status_code=503, content={"status": "not-ready", "reason": str(exc)[:200]})


@app.websocket("/ws/campaign/{campaign_id}")
async def campaign_ws(websocket: WebSocket, campaign_id: str) -> None:
    """campaign:{id} 频道事件中继（技术方案 6.6）。"""
    await websocket.accept()
    try:
        async for event in bus.subscribe(Channel.campaign, campaign_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:  # pragma: no cover - 客户端主动断开
        pass
    except Exception:  # pragma: no cover - 传输异常
        pass


@app.websocket("/ws/session/{session_id}")
async def session_ws(websocket: WebSocket, session_id: str) -> None:
    """sessions:{id} 频道事件中继。"""
    await websocket.accept()
    try:
        async for event in bus.subscribe(Channel.session, session_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:  # pragma: no cover - 客户端主动断开
        pass
    except Exception:  # pragma: no cover - 传输异常
        pass