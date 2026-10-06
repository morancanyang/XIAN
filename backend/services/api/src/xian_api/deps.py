"""依赖注入：配置、数据库会话、当前租户与角色（PRD 1.3 角色与权限）。"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from xian_core.config import Settings, get_settings
from xian_core.db.session import get_session

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


class Principal:
    """请求主体：租户 + 用户 + 角色。生产态由 JWT 解析，开发态可由 Header 注入。"""

    def __init__(self, tenant_id: uuid.UUID, user_id: uuid.UUID, role: str) -> None:
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.role = role

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def can(self, action: str) -> bool:
        return action in ROLE_PERMISSIONS.get(self.role, set())


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"agent:write", "agent:read", "scenario:write", "campaign:run", "report:read",
              "report:export", "weapon:export", "level:play", "audit:read", "member:manage"},
    "red": {"agent:read", "campaign:run", "report:read", "report:export", "level:play"},
    "blue": {"agent:write", "agent:read", "scenario:write", "campaign:run", "report:read",
             "report:export", "level:play"},
    "viewer": {"agent:read", "report:read", "level:play"},
}

ROLE_ORDER = ("admin", "red", "blue", "viewer")


async def get_principal(
    x_tenant_id: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
    x_role: Annotated[str | None, Header()] = "blue",
) -> Principal:
    """开发态简版鉴权：Header 注入身份；生产态替换为 JWT/OIDC 校验。"""
    try:
        tenant_id = uuid.UUID(x_tenant_id) if x_tenant_id else uuid.uuid4()
        user_id = uuid.UUID(x_user_id) if x_user_id else uuid.uuid4()
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "X-Tenant-Id / X-User-Id 必须是合法 UUID") from exc
    role = (x_role or "blue").lower()
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"未知角色 {role}")
    return Principal(tenant_id=tenant_id, user_id=user_id, role=role)


PrincipalDep = Annotated[Principal, Depends(get_principal)]


def require(action: str):
    """RBAC 守卫：无权限直接 403（PRD 3.9.4）。"""

    async def _guard(principal: PrincipalDep) -> Principal:
        if not principal.can(action):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"角色 {principal.role} 无权执行 {action}")
        return principal

    return _guard


async def get_tenant_id(principal: PrincipalDep) -> uuid.UUID:
    return principal.tenant_id