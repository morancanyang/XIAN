"""报告分享链接：有效期、密码、水印（PRD 3.8.4.4）。"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from ..errors import ValidationError


@dataclass(frozen=True, slots=True)
class ShareLink:
    token: str
    password_hash: str
    expired_at: datetime
    watermark: str
    max_views: int = 0
    views: int = 0

    @property
    def expired(self) -> bool:
        return datetime.now().astimezone() > self.expired_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "expired_at": self.expired_at.isoformat(),
            "watermark": self.watermark,
            "max_views": self.max_views,
            "views": self.views,
        }


def create_share(*, password: str | None = None, ttl_hours: int = 72, watermark: str = "XIAN 内部资料", max_views: int = 0) -> ShareLink:
    if ttl_hours <= 0:
        raise ValidationError("分享链接有效期必须为正数")
    digest = hashlib.sha256((password or "").encode("utf-8")).hexdigest() if password else ""
    return ShareLink(
        token=secrets.token_urlsafe(24),
        password_hash=digest,
        expired_at=datetime.now().astimezone() + timedelta(hours=ttl_hours),
        watermark=watermark,
        max_views=max_views,
    )


def check_access(link: ShareLink, *, password: str | None = None) -> tuple[bool, str]:
    if link.expired:
        return False, "链接已失效"
    if link.password_hash:
        if not password:
            return False, "该链接需要访问密码"
        if hashlib.sha256(password.encode("utf-8")).hexdigest() != link.password_hash:
            return False, "访问密码不正确"
    if link.max_views and link.views >= link.max_views:
        return False, "链接访问次数已用尽"
    return True, "ok"


def register_view(link: ShareLink) -> ShareLink:
    object.__setattr__(link, "views", link.views + 1)
    return link