"""pytest 公共夹具：内存库 + 测试租户 + 离线 LLM 网关。

所有测试默认使用 SQLite 内存库与确定性离线回放（``LLMGateway._offline_complete``），
不依赖外部服务；接入 Postgres / Redis / ClickHouse 的集成用例通过 ``--with-infra`` 开关开启。
"""

from __future__ import annotations

import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import UUID

import pytest

os.environ.setdefault("XIAN_DB_DSN_OVERRIDE", "sqlite+aiosqlite://")

# LLM 一律走确定性离线回放。用显式清空而不是 setdefault：否则单独跑本目录时
# 会继承开发机上的真实 Key（如 DEEPSEEK_API_KEY），配置推断会把网关判成在线。
os.environ["XIAN_LLM_BASE_URL"] = ""
os.environ["XIAN_LLM_API_KEY"] = ""
for _key_env in ("DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "DASHSCOPE_API_KEY",
                 "SILICONFLOW_API_KEY", "ZHIPU_API_KEY", "OPENAI_API_KEY"):
    os.environ.pop(_key_env, None)

ROOT = Path(__file__).resolve().parents[4]
for extra in ("libs/xian_core/src", "services/api", "services/worker", "services/cli"):
    p = ROOT / extra
    if p.is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
AGENT_ID = UUID("33333333-3333-3333-3333-333333333333")
CAMPAIGN_ID = UUID("44444444-4444-4444-4444-444444444444")


@pytest.fixture(autouse=True)
def _clean_settings_cache():
    from xian_core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
async def engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    from xian_core.db import models  # noqa: F401  # 注册全部模型
    from xian_core.db.base import Base

    eng = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False})
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture()
async def session(engine) -> AsyncGenerator:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as sess:
        yield sess
        await sess.rollback()


@pytest.fixture()
def tenant_id() -> UUID:
    return TENANT_ID


@pytest.fixture()
def user_id() -> UUID:
    return USER_ID


@pytest.fixture()
def agent_id() -> UUID:
    return AGENT_ID


@pytest.fixture()
def campaign_id() -> UUID:
    return CAMPAIGN_ID
