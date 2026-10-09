"""依赖注入：配置、数据库会话、当前租户与角色（PRD 1.3 角色与权限）。"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

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


def _decode_bearer(authorization: str) -> dict[str, Any]:
    """解析 ``Authorization: Bearer <jwt>``；格式不符或验签失败一律 401。

    延迟导入：routers 包初始化时会 import 本模块，顶层写 ``from .auth import ...``
    会形成 deps -> routers -> deps 的循环依赖。
    """
    from .routers.auth import decode_token

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authorization 头需为 Bearer <token>")
    return decode_token(token.strip())


async def get_principal(
    x_tenant_id: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
    x_role: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    """请求主体解析：显式 Header 覆盖 > JWT 声明 > 开发态随机身份。

    原实现只读 Header，注册/登录签出的 JWT 在鉴权链路上从未被消费——不带 Header 的
    调用方（curl、脚本、服务间调用）每次请求都会拿到一个随机租户，刚创建的资源下一个
    请求就 404"不存在"。这里把 JWT 补成第二优先级，同时保持前端既有行为不变：

    - 三个显式 Header 仍是最高优先级（管理端 impersonate 与前端默认上下文沿用），
      所以老数据不会因为切到 JWT 而"消失"；
    - 缺哪个字段才解析 token；token 格式错误或验签失败直接 401，不静默放过；
    - 两者都没有时维持原样的随机身份，开发态零配置可跑。
    """
    claims: dict[str, Any] = {}
    # 只在确实缺字段时才解析 token：显式 Header 是覆盖语义，不该被 token 干扰
    if authorization and not (x_tenant_id and x_user_id and x_role):
        claims = _decode_bearer(authorization)

    tenant_raw = x_tenant_id or str(claims.get("tenant_id") or "")
    user_raw = x_user_id or str(claims.get("sub") or "")
    role_raw = x_role or str(claims.get("role") or "")

    try:
        tenant_id = uuid.UUID(tenant_raw) if tenant_raw else uuid.uuid4()
        user_id = uuid.UUID(user_raw) if user_raw else uuid.uuid4()
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "X-Tenant-Id / X-User-Id 必须是合法 UUID"
        ) from exc
    role = (role_raw or "blue").lower()
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