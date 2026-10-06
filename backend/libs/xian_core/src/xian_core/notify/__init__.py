"""通知分发：邮件 / IM Webhook / 站内信，失败降级（PRD 3.3.6.8.1、3.8.4.8.1）。"""

from .channels import MAX_RETRIES, EmailChannel, InAppChannel, Notification, WebhookChannel, build_alert
from .dispatcher import DispatchReport, NotifyDispatcher

__all__ = [
    "MAX_RETRIES",
    "DispatchReport",
    "EmailChannel",
    "InAppChannel",
    "Notification",
    "NotifyDispatcher",
    "WebhookChannel",
    "build_alert",
]