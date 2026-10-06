"""Celery 应用与 beat 调度（技术方案 3.2 / 4.5）。

broker/backend 均使用 Redis；队列按业务隔离，避免慢任务阻塞巡检与通知。
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from xian_core.config import get_settings

settings = get_settings()

app = Celery(
    "xian",
    broker=settings.bus.celery_broker,
    backend=settings.bus.celery_backend,
    include=["xian_worker.tasks.campaign", "xian_worker.tasks.retest",
             "xian_worker.tasks.report_render", "xian_worker.tasks.scan",
             "xian_worker.tasks.notify"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,
    task_default_queue="xian.default",
    task_routes={
        "xian_worker.tasks.campaign.*": {"queue": "xian.campaign"},
        "xian_worker.tasks.retest.*": {"queue": "xian.retest"},
        "xian_worker.tasks.report_render.*": {"queue": "xian.report"},
        "xian_worker.tasks.scan.*": {"queue": "xian.scan"},
        "xian_worker.tasks.notify.*": {"queue": "xian.notify"},
    },
    broker_connection_retry_on_startup=True,
)

app.conf.beat_schedule = {
    "scheduled-patrol": {
        "task": "xian_worker.tasks.scan.scheduled_patrol",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "xian.scan"},
    },
    "weekly-digest": {
        "task": "xian_worker.tasks.notify.weekly_digest",
        "schedule": crontab(day_of_week="mon", hour=9, minute=0),
        "options": {"queue": "xian.notify"},
    },
    "instance-reaper": {
        "task": "xian_worker.tasks.campaign.reap_expired_instances",
        "schedule": crontab(minute="*/10"),
        "options": {"queue": "xian.campaign"},
    },
}

__all__ = ["app"]