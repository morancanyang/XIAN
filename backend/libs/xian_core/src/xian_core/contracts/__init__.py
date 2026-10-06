"""Celery 任务签名与 WS/SSE 事件契约。

注意：``contracts`` 只放任务签名与事件契约；领域 Pydantic 模型在 ``schemas``，二者职责不重叠。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------- 任务签名
TaskName = Literal[
    "run_campaign",
    "finalize_campaign",
    "render_report",
    "run_retest",
    "run_scan",
    "archive_session",
    "dispatch_notification",
    "scheduled_patrol",
]


class TaskEnvelope(BaseModel):
    """Celery 任务统一信封：保证 api ↔ worker 只经消息与数据库通信（技术方案 4.5）。"""

    task: str
    tenant_id: str
    subject_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = ""
    attempt: int = 0


class CampaignTaskPayload(BaseModel):
    campaign_id: str
    agent_id: str
    scenario_instance_id: str
    intensity: str
    budget: dict[str, Any] = Field(default_factory=dict)
    scope: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class RetestTaskPayload(BaseModel):
    remediation_run_id: str
    recommendation_id: str
    campaign_id: str
    record_ids: list[str] = Field(default_factory=list)
    include_regression: bool = True


class RenderReportTaskPayload(BaseModel):
    report_id: str
    formats: list[str] = Field(default_factory=lambda: ["html", "json"])


class ScanTaskPayload(BaseModel):
    scan_job_id: str
    agent_id: str
    agent_version_id: str | None = None
    preset_id: str = "quick"
    ci_context: dict[str, Any] = Field(default_factory=dict)


class NotifyTaskPayload(BaseModel):
    notification_id: str
    channels: list[str] = Field(default_factory=list)
    recipients: list[str] = Field(default_factory=list)
    title: str = ""
    body: str = ""


# ---------------------------------------------------------------- 事件契约
class WsEnvelope(BaseModel):
    """campaign:{id} / sessions:{id} 频道事件信封（技术方案 6.6）。"""

    ts: int
    type: str
    role: str = "system"
    message: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    campaign_id: str | None = None
    session_id: str | None = None


class ExitCode(int):
    """CI 门禁退出码（xian scan）。"""

    PASS = 0
    FAIL = 1
    INDETERMINATE = 2


__all__ = [
    "CampaignTaskPayload",
    "ExitCode",
    "NotifyTaskPayload",
    "RenderReportTaskPayload",
    "RetestTaskPayload",
    "ScanTaskPayload",
    "TaskEnvelope",
    "TaskName",
    "WsEnvelope",
]