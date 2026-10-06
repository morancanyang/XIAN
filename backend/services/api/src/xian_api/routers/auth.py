"""账号与登录（PRD 3.9.4）。开发态为本地 JWT，生产态对接 OIDC/LDAP。"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from threading import Lock

import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from xian_core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

ALGORITHM = "HS256"

# 开发态自助注册角色与登录表单保持一致；生产态应收紧为 red/blue/analyst（admin 由管理员提升）。
REGISTER_ROLES = ("red", "blue", "analyst", "admin")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PBKDF2_ROUNDS = 120_000


class LoginIn(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)
    tenant_id: str | None = None


class RegisterIn(BaseModel):
    """自助注册入参：邮箱即账号，密码至少 6 位（生产态由真实身份源接管）。"""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=6, max_length=128)
    role: str = "blue"
    tenant_id: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    tenant_id: str
    user_id: str


def issue_token(*, user_id: str, tenant_id: str, role: str, ttl_minutes: int = 480) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.security.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.security.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(401, f"token 无效或已过期：{exc}") from exc


def normalize_email(email: str) -> str:
    """账号统一小写去空格，避免大小写导致同一账号被当成两个。"""
    return email.strip().lower()


def tenant_for(email: str, tenant_id: str | None) -> str:
    """未显式指定租户时按账号派生稳定租户，保证同一账号多次登录拿到同一上下文。"""
    return tenant_id or str(uuid.uuid5(uuid.NAMESPACE_URL, f"tenant:{email}"))


def user_for(email: str) -> str:
    """账号 → 稳定 user_id（开发态无需持久化用户表即可对齐后续数据归属）。"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, email))


def _hash_password(password: str, salt: str) -> str:
    """PBKDF2-SHA256 派生：注册表只保存摘要与盐，不明文保存口令。"""
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return digest.hex()


class AccountRegistry:
    """开发态账号注册表：进程内保存自助注册的账号（重启后失效，生产态由真实身份源接管）。

    已注册账号登录时必须校验密码；未注册账号仍走开发态「任意密码可登录」回退，
    避免破坏 demo@xian.local 等既有演示账号的登录体验。
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._accounts: dict[str, dict[str, str]] = {}

    def register(self, *, email: str, password: str, role: str, tenant_id: str) -> None:
        salt = secrets.token_hex(16)
        entry = {
            "password_hash": _hash_password(password, salt),
            "salt": salt,
            "role": role,
            "tenant_id": tenant_id,
        }
        with self._lock:
            if email in self._accounts:
                raise HTTPException(409, "该账号已注册，请直接登录")
            self._accounts[email] = entry

    def role_of(self, email: str) -> str | None:
        with self._lock:
            entry = self._accounts.get(email)
            return entry["role"] if entry else None

    def verify(self, email: str, password: str) -> bool | None:
        """已注册账号返回校验结果；未注册返回 None，交由调用方走开发态回退。"""
        with self._lock:
            entry = self._accounts.get(email)
        if entry is None:
            return None
        candidate = _hash_password(password, entry["salt"])
        return hmac.compare_digest(candidate, entry["password_hash"])


accounts = AccountRegistry()


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(payload: RegisterIn) -> TokenOut:
    """自助注册：校验通过后直接签发 token，免去二次登录（PRD 3.9.4）。"""
    email = normalize_email(payload.email)
    if not EMAIL_PATTERN.match(email):
        raise HTTPException(400, "账号需为合法邮箱格式，例如 name@xian.local")
    if payload.role not in REGISTER_ROLES:
        raise HTTPException(400, f"非法角色 {payload.role}，可选：{'/'.join(REGISTER_ROLES)}")
    tenant_id = tenant_for(email, payload.tenant_id)
    accounts.register(email=email, password=payload.password, role=payload.role, tenant_id=tenant_id)
    user_id = user_for(email)
    token = issue_token(user_id=user_id, tenant_id=tenant_id, role=payload.role)
    return TokenOut(
        access_token=token,
        expires_in=480 * 60,
        role=payload.role,
        tenant_id=tenant_id,
        user_id=user_id,
    )


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn) -> TokenOut:
    """登录：已注册账号校验密码；未注册账号为开发态演示，任意密码均可登录（生产态替换为真实身份源）。"""
    email = normalize_email(payload.email)
    tenant_id = tenant_for(email, payload.tenant_id)
    user_id = user_for(email)
    role = accounts.role_of(email)
    if role is None:
        role = "admin" if email.startswith("admin") else "blue"
    elif accounts.verify(email, payload.password) is not True:
        raise HTTPException(401, "账号或密码错误，请重试")
    token = issue_token(user_id=user_id, tenant_id=tenant_id, role=role)
    return TokenOut(
        access_token=token, expires_in=480 * 60, role=role, tenant_id=tenant_id, user_id=user_id
    )


@router.get("/me")
async def me(authorization: str = "") -> dict:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "缺少 Bearer token")
    claims = decode_token(authorization[7:])
    return {"user_id": claims.get("sub"), "tenant_id": claims.get("tenant_id"), "role": claims.get("role")}