"""请求主体解析优先级：显式 Header 覆盖 > JWT 声明 > 开发态随机身份。

背景：``get_principal`` 原先只读 X-Tenant-Id / X-User-Id / X-Role，注册登录签出的
JWT 在鉴权链路上从未被消费。不带 Header 的调用方（curl、脚本、服务间调用）每次请求
都会拿到一个随机租户——建完会话/Agent，下一个请求就 404"不存在"。
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    os.environ.setdefault("XIAN_DB_DSN_OVERRIDE", "sqlite+aiosqlite://")
    from xian_api.main import app

    with TestClient(app) as c:
        yield c


def _token(*, user_id: str | None = None, tenant_id: str | None = None, role: str = "blue") -> str:
    from xian_api.routers.auth import issue_token

    return issue_token(
        user_id=user_id or str(uuid4()),
        tenant_id=tenant_id or str(uuid4()),
        role=role,
    )


def _create_agent(client: TestClient, headers: dict[str, str]) -> dict:
    resp = client.post(
        "/api/v1/agents",
        json={"name": "主体解析探针", "access_type": "http", "endpoint": "http://x"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_headers_take_precedence_over_token(client: TestClient) -> None:
    """前端同时发 Header 与 Bearer：Header 必须是覆盖项，老数据不能因切 JWT 而消失。"""
    header_tenant, header_user = str(uuid4()), str(uuid4())
    token = _token(tenant_id=str(uuid4()), user_id=str(uuid4()), role="red")
    agent = _create_agent(client, {
        "X-Tenant-Id": header_tenant,
        "X-User-Id": header_user,
        "X-Role": "admin",
        "Authorization": f"Bearer {token}",
    })
    assert agent["tenant_id"] == header_tenant


def test_token_supplies_identity_when_headers_absent(client: TestClient) -> None:
    """只带 Bearer：身份来自 JWT，且同一 token 多次请求必须稳定（原实现每次随机）。"""
    tenant_id, user_id = str(uuid4()), str(uuid4())
    headers = {"Authorization": f"Bearer {_token(tenant_id=tenant_id, user_id=user_id)}"}

    first = _create_agent(client, headers)["tenant_id"]
    second = _create_agent(client, headers)["tenant_id"]
    assert first == second == tenant_id


def test_no_credentials_falls_back_to_random_identity(client: TestClient) -> None:
    """两者都没有时维持原样的随机身份：开发态零配置仍可跑通。"""
    first = _create_agent(client, {})["tenant_id"]
    second = _create_agent(client, {})["tenant_id"]
    assert first != second


def test_malformed_token_is_rejected(client: TestClient) -> None:
    """token 验签失败必须 401，不能静默放过伪造凭证。"""
    resp = client.post(
        "/api/v1/agents",
        json={"name": "x", "access_type": "http", "endpoint": "http://x"},
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert resp.status_code == 401


def test_non_bearer_authorization_is_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/agents",
        json={"name": "x", "access_type": "http", "endpoint": "http://x"},
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert resp.status_code == 401


def test_role_from_token_is_enforced(client: TestClient) -> None:
    """JWT 里的角色要参与 RBAC：viewer 无权建 Agent。"""
    resp = client.post(
        "/api/v1/agents",
        json={"name": "x", "access_type": "http", "endpoint": "http://x"},
        headers={"Authorization": f"Bearer {_token(role='viewer')}"},
    )
    assert resp.status_code == 403


def test_bad_tenant_header_is_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/agents",
        json={"name": "x", "access_type": "http", "endpoint": "http://x"},
        headers={"X-Tenant-Id": "not-a-uuid"},
    )
    assert resp.status_code == 400
