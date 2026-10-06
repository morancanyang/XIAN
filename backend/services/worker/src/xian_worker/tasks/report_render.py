"""报告渲染任务（PRD 3.8.4.6 导出超时转异步）。"""

from __future__ import annotations

from typing import Any

from xian_core.reports import build_report_payload, export

from ..celery_app import app


@app.task(name="xian_worker.tasks.report_render.render_report", bind=True, max_retries=1)
def render_report(self, payload: dict[str, Any]) -> dict[str, Any]:
    report_id = str(payload["report_id"])
    formats = list(payload.get("formats", ["html", "json"]))
    data = build_report_payload(
        tenant_id=str(payload.get("tenant_id", "")),
        subject_type=str(payload.get("subject_type", "campaign")),
        subject_id=report_id,
        agent=dict(payload.get("agent", {})),
        records=list(payload.get("records", [])),
    )
    artifacts = export(payload=data, formats=formats, desensitize_level=str(payload.get("desensitize_level", "standard")))
    return {"report_id": report_id, "artifacts": [a.to_dict() for a in artifacts]}