"""数据库会话与引擎（异步 SQLAlchemy 2.0）。"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        kwargs: dict[str, object] = {"echo": settings.db.echo}
        if settings.db.dsn.startswith("postgresql"):
            kwargs.update(
                pool_size=settings.db.pool_size,
                max_overflow=settings.db.max_overflow,
                pool_pre_ping=True,
            )
        elif settings.db.dsn.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_async_engine(settings.db.dsn, **kwargs)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(), class_=AsyncSession, expire_on_commit=False, autoflush=False
        )
    return _sessionmaker


async def init_db() -> None:
    """建表（开发/测试用；生产走 Alembic 迁移）。"""
    from . import models  # noqa: F401  # 注册全部模型
    from .base import Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    maker = get_sessionmaker()
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入用。"""
    maker = get_sessionmaker()
    async with maker() as session:
        yield session