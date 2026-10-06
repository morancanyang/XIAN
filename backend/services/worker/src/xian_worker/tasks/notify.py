"""通知分发任务（PRD 3.3.6.8.1 / 3.8.4.8.1）。"""

from __future__ import annotations

from typing import Any

from xian_core.notify import NotifyDispatcher, build_alert

from ..celery_app import app


@app.task(name="xian_worker.tasks.notify.dispatch_notification", bind=True, max_retries=3)
def dispatch_notification(self, payload: dict[str, Any]) -> dict[str, Any]:
    notifications = build_alert(
        subject=str(payload.get("title", "XIAN 通知")),
        body=str(payload.get("body", "")),
        severity=str(payload.get("severity", "info")),
        recipients=list(payload.get("recipients", [])),
        channels=list(payload.get("channels", ["inapp"])),
    )
    report = NotifyDispatcher().dispatch(notifications)
    return report.to_dict()


@app.task(name="xian_worker.tasks.notify.weekly_digest")
def weekly_digest() -> dict[str, Any]:
    """周报摘要推送（PRD 3.8.4.8.1）。"""
    from xian_core.reports import build_digest

    return build_digest(period="weekly", campaigns=[])