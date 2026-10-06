"""通知渠道：邮件 / IM Webhook / 站内信（PRD 3.3.6.8.1、3.8.4.8.1）。"""

from __future__ import annotations

import smtplib
from collections.abc import Iterable
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any

MAX_RETRIES = 3


@dataclass(slots=True)
class Notification:
    channel: str
    recipient: str
    subject: str
    body: str
    severity: str = "info"
    retries: int = 0
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
            "severity": self.severity,
            "retries": self.retries,
            "status": self.status,
        }


class EmailChannel:
    """SMTP 邮件渠道；未配置时自动降级，由 dispatcher 转站内信。"""

    def __init__(self, *, host: str = "", port: int = 465, user: str = "", password: str = "", sender: str = "xian@example.com", use_ssl: bool = True) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender
        self.use_ssl = use_ssl

    @property
    def configured(self) -> bool:
        return bool(self.host and self.user)

    def send(self, notification: Notification) -> bool:
        if not self.configured:
            raise RuntimeError("SMTP 未配置")
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = notification.recipient
        msg["Subject"] = notification.subject
        msg.set_content(notification.body)
        cls = smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP
        with cls(self.host, self.port, timeout=15) as smtp:
            if self.user:
                smtp.login(self.user, self.password)
            smtp.send_message(msg)
        return True


class WebhookChannel:
    """IM Webhook（兼容飞书/钉钉/企业微信机器人文本消息）。"""

    def __init__(self, *, url: str = "", timeout: float = 10.0) -> None:
        self.url = url
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.url)

    def send(self, notification: Notification) -> bool:
        if not self.configured:
            raise RuntimeError("Webhook 未配置")
        import httpx

        payload = {
            "msgtype": "text",
            "text": {"content": f"[XIAN][{notification.severity}] {notification.subject}\n{notification.body}"},
        }
        resp = httpx.post(self.url, json=payload, timeout=self.timeout)
        return resp.status_code < 300


class InAppChannel:
    """站内信：始终可用，是所有渠道失败后的兜底（PRD 3.8.4.8.1 异常分支）。"""

    def __init__(self) -> None:
        self.inbox: list[Notification] = []

    @property
    def configured(self) -> bool:
        return True

    def send(self, notification: Notification) -> bool:
        notification.status = "sent"
        self.inbox.append(notification)
        return True


def build_alert(*, subject: str, body: str, severity: str = "high", recipients: Iterable[str], channels: Iterable[str]) -> list[Notification]:
    """按渠道 × 接收人展开通知（PRD 3.3.6.8.1）。"""
    recipients = list(recipients) or [""]
    channels = list(channels) or ["inapp"]
    return [
        Notification(channel=ch, recipient=rc, subject=subject, body=body, severity=severity)
        for ch in channels
        for rc in recipients
    ]