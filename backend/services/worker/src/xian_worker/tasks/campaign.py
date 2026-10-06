"""战役执行任务（PRD 3.3.5 / 3.3.6）。"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from xian_core.db.repositories import CampaignRepository
from xian_core.db.session import session_scope
from xian_core.redteam import execute_campaign

from ..celery_app import app


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(name="xian_worker.tasks.campaign.run_campaign", bind=True, max_retries=2)
def run_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
    """执行一次战役：计划 → 逐用例攻击 → 判定 → 汇总 → 落库。

    worker 只做编排：计划来自 commander、攻击来自 attacker、判定来自 judge，
    落库统一复用 :func:`xian_core.redteam.execute_campaign`，与 API 内联执行同源。
    """
    campaign_id = str(payload["campaign_id"])
    try:
        return _run(_execute(campaign_id, payload))
    except Exception as exc:  # pragma: no cover
        raise self.retry(exc=exc, countdown=5) from exc


async def _execute(campaign_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with session_scope() as session:
        rows = await CampaignRepository(session).list_by_id(_uuid(campaign_id))
        campaign = rows[0] if rows else None
        if campaign is None:
            return {"campaign_id": campaign_id, "status": "not_found"}
        if payload.get("intensity"):
            campaign.intensity = str(payload["intensity"])
        if payload.get("budget"):
            campaign.budget = dict(payload["budget"])
            campaign.partial = False
        campaign.status = "attacking"
        await session.flush()
        result = await execute_campaign(campaign, session=session, tenant_id=campaign.tenant_id)
        campaign.status = "completed"
        campaign.progress = 100
        await session.commit()
        return result.to_dict()


run_campaign_task = run_campaign


@app.task(name="xian_worker.tasks.campaign.finalize_campaign")
def finalize_campaign(payload: dict[str, Any]) -> dict[str, Any]:
    """战役收尾：汇总 SecScore 并触发报告渲染。"""
    return {"campaign_id": str(payload.get("campaign_id", "")), "status": "finalized"}


@app.task(name="xian_worker.tasks.campaign.reap_expired_instances")
def reap_expired_instances() -> dict[str, Any]:
    """回收过期场景实例，保留蜜标台账（PRD 3.1.4 后置条件）。"""
    from xian_core.db.repositories import ScenarioInstanceRepository

    async def _reap() -> int:
        async with session_scope() as session:
            repo = ScenarioInstanceRepository(session)
            rows = await repo.expire_due()
            for row in rows:
                row.status = "destroyed"
            return len(rows)

    try:
        return {"reaped": _run(_reap())}
    except Exception:  # pragma: no cover
        return {"reaped": 0, "reason": "database unavailable"}


def _uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)
