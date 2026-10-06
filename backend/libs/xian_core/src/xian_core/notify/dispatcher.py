"""通知分发器：失败重试 3 次后降级为站内信（PRD 3.8.4.8.1）。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .channels import MAX_RETRIES, EmailChannel, InAppChannel, Notification, WebhookChannel


@dataclass(slots=True)
class DispatchReport:
    sent: list[dict[str, Any]] = field(default_factory=list)
    downgraded: list[dict[str, Any]] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"sent": self.sent, "downgraded": self.downgraded, "failed": self.failed}


class NotifyDispatcher:
    def __init__(
        self,
        *,
        email: EmailChannel | None = None,
        webhook: WebhookChannel | None = None,
        inapp: InAppChannel | None = None,
    ) -> None:
        self.email = email or EmailChannel()
        self.webhook = webhook or WebhookChannel()
        self.inapp = inapp or InAppChannel()

    def _channel_for(self, name: str):
        return {"email": self.email, "webhook": self.webhook, "inapp": self.inapp}.get(name, self.inapp)

    def dispatch(self, notifications: Iterable[Notification]) -> DispatchReport:
        report = DispatchReport()
        for notification in notifications:
            channel = self._channel_for(notification.channel)
            if not channel.configured:
                self._downgrade(notification, report, f"渠道 {notification.channel} 未配置")
                continue
            ok = False
            last_error = ""
            for _ in range(MAX_RETRIES):
                try:
                    ok = channel.send(notification)
                    break
                except Exception as exc:
                    last_error = str(exc)
                    notification.retries += 1
            if ok:
                report.sent.append(notification.to_dict())
            else:
                self._downgrade(notification, report, last_error or "发送失败")
        return report

    def _downgrade(self, notification: Notification, report: DispatchReport, reason: str) -> None:
        fallback = Notification(
            channel="inapp",
            recipient=notification.recipient,
            subject=notification.subject,
            body=f"{notification.body}\n\n[原渠道 {notification.channel} 失败：{reason}]",
            severity=notification.severity,
        )
        self.inapp.send(fallback)
        report.downgraded.append({**notification.to_dict(), "reason": reason})