"""worker：任务路由 beat 编排、任务可导入、退出码契约。"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("XIAN_DB_DSN_OVERRIDE", "sqlite+aiosqlite://")


@pytest.fixture(autouse=True)
async def _schema():
    """为需要数据库的 worker 测试建表。"""
    from sqlalchemy.ext.asyncio import create_async_engine
    from xian_core.db import models  # noqa: F401  # 注册全部模型
    from xian_core.db import session as session_module
    from xian_core.db.base import Base

    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_module._engine = engine
    session_module._sessionmaker = None
    yield
    session_module._engine = None
    session_module._sessionmaker = None
    await engine.dispose()

def test_celery_app_has_five_queues() -> None:

    from xian_worker.celery_app import app

    routes = app.conf.task_routes

    assert routes, "应配置任务路由"

    queues = {spec.get("queue") for spec in routes.values()}

    assert {"xian.campaign", "xian.retest", "xian.report", "xian.scan", "xian.notify"} <= queues

def test_celery_beat_schedule_registers_maintenance_tasks() -> None:

    from xian_worker.celery_app import app

    schedule = app.conf.beat_schedule

    assert any("patrol" in key for key in schedule), "应注册每日巡检"

    assert any("reaper" in key for key in schedule), "应注册实例回收"

    assert any("digest" in key for key in schedule), "应注册周报订阅"

def test_task_module_imports_cleanly() -> None:

    from xian_worker.tasks import campaign, notify, report_render, retest, scan

    assert callable(campaign.run_campaign)

    assert callable(campaign.reap_expired_instances)

    assert callable(scan.run_scan)

    assert callable(scan.scheduled_patrol)

    assert callable(report_render.render_report)

    assert callable(notify.dispatch_notification)

    assert callable(notify.weekly_digest)

    assert callable(retest.run_retest)

def test_run_scan_exit_code_contract() -> None:

    from xian_worker.tasks.scan import run_scan

    ok = run_scan({"current_score": 95, "previous_score": 92})

    assert ok["exit_code"] == 0 and ok["passed"]

    bad = run_scan({"current_score": 80, "previous_score": 95})

    assert bad["exit_code"] == 1 and not bad["passed"]

    assert bad["reasons"]

def test_campaign_task_returns_not_found_for_unknown_id() -> None:

    from xian_worker.tasks.campaign import run_campaign

    result = run_campaign({"campaign_id": "00000000-0000-0000-0000-000000000000"})

    assert result["status"] == "not_found"

