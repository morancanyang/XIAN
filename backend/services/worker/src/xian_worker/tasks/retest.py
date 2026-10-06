"""一键复测任务（PRD 3.7.5）。"""

from __future__ import annotations

import asyncio
from typing import Any

from xian_core.remediation import evaluate_retest

from ..celery_app import app


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(name="xian_worker.tasks.retest.run_retest", bind=True, max_retries=2)
def run_retest(self, payload: dict[str, Any]) -> dict[str, Any]:
    """对同一场景实例复跑历史用例，比较加固前后分数与 ASR。

    复测失败（分数未升或可用性受损）自动回滚并通知（PRD 3.7.5 后置条件）。
    """
    result = evaluate_retest(
        before_sec_score=int(payload.get("before_sec_score", 0)),
        after_sec_score=int(payload.get("after_sec_score", 0)),
        before_asr=float(payload.get("before_asr", 0.0)),
        after_asr=float(payload.get("after_asr", 0.0)),
        baseline_pass_rate=float(payload.get("baseline_pass_rate", 1.0)),
    )
    return {
        "recommendation_id": str(payload.get("recommendation_id", "")),
        "status": result.status,
        "rolled_back": result.rolled_back,
        "before_sec_score": result.before_sec_score,
        "after_sec_score": result.after_sec_score,
        "regression_pass_rate": result.regression_pass_rate,
    }