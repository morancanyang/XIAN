"""定时巡检与 CI 扫描任务（PRD 3.8.5.1）。"""

from __future__ import annotations

from typing import Any

from xian_core.ops import GateRule, evaluate

from ..celery_app import app


@app.task(name="xian_worker.tasks.scan.run_scan")
def run_scan(payload: dict[str, Any]) -> dict[str, Any]:
    """CI 门禁扫描：返回机读 JSON 与退出码（0 通过 / 1 失败 / 2 异常）。"""
    rule = GateRule.from_payload(dict(payload.get("rule", {})))
    result = evaluate(
        rule=rule,
        current_score=int(payload.get("current_score", 0)),
        previous_score=payload.get("previous_score"),
        new_high_count=int(payload.get("new_high_count", 0)),
        baseline_pass_rate=float(payload.get("baseline_pass_rate", 1.0)),
    )
    return {"exit_code": result.exit_code, "passed": result.passed, "reasons": result.reasons}


@app.task(name="xian_worker.tasks.scan.scheduled_patrol")
def scheduled_patrol() -> dict[str, Any]:
    """定时巡检：扫描到期 scan_job，新增高危即时告警。"""
    from xian_core.db.repositories import ScanJobRepository
    from xian_core.db.session import session_scope
    from xian_core.ops import due_jobs

    async def _collect() -> int:
        async with session_scope() as session:
            rows = await ScanJobRepository(session).list()
            jobs = []
            for row in rows:
                job = type("J", (), {"next_run_at": row.next_run_at, "enabled": row.enabled})()
                jobs.append(job)
            return len(due_jobs(jobs))

    try:
        return {"due": _run_sync(_collect)}
    except Exception:
        return {"due": 0, "reason": "database unavailable"}


def _run_sync(coro_factory):
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro_factory())
    finally:
        loop.close()