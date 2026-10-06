"""接入凭据的加密存储、轮换与撤销（PRD 3.2.4 数据字典 agent_credential）。"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet  # type: ignore[import-untyped]


def _derive(master: str) -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(master.encode("utf-8")).digest())


@dataclass(slots=True)
class Credential:
    token: str
    scope: str
    expired_at: datetime
    rotated_from: str | None = None
    revoked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "expired_at": self.expired_at.isoformat(),
            "rotated_from": self.rotated_from,
            "revoked": self.revoked,
        }


class CredentialVault:
    """对称加密保管 Agent 接入 token；密钥来自环境变量，绝不落库明文。"""

    def __init__(self, master_key: str) -> None:
        self._fernet = Fernet(_derive(master_key))

    def encrypt(self, token: str) -> str:
        return self._fernet.encrypt(token.encode("utf-8")).decode("utf-8")

    def decrypt(self, cipher: str) -> str:
        return self._fernet.decrypt(cipher.encode("utf-8")).decode("utf-8")

    @staticmethod
    def mint(scope: str = "agent:invoke", *, ttl_days: int = 90) -> Credential:
        return Credential(
            token=f"xian_{secrets.token_urlsafe(32)}",
            scope=scope,
            expired_at=datetime.now().astimezone() + timedelta(days=ttl_days),
        )

    @staticmethod
    def rotate(old: Credential, *, ttl_days: int = 90) -> Credential:
        fresh = CredentialVault.mint(old.scope, ttl_days=ttl_days)
        fresh.rotated_from = _fingerprint(old.token)
        old.revoked = True
        return fresh

    @staticmethod
    def revoke(cred: Credential) -> Credential:
        cred.revoked = True
        return cred

    @staticmethod
    def is_valid(cred: Credential) -> bool:
        return not cred.revoked and cred.expired_at > datetime.now().astimezone()


def _fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]