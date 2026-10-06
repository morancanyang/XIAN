"""账号注册 / 登录契约测试（PRD 3.9.4）。

覆盖开发态账号注册表：注册成功即签发 token、重复注册 409、已注册账号登录需校验密码，
未注册的演示账号仍走「任意密码可登录」的开发态回退。
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    os.environ.setdefault("XIAN_DB_DSN_OVERRIDE", "sqlite+aiosqlite://")
    from xian_api.main import app

    with TestClient(app) as c:
        yield c


def test_register_issues_token_with_requested_role(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "red.op@xian.local", "password": "red123456", "role": "red"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "red"
    assert body["user_id"] and body["tenant_id"]
    assert body["access_token"]


def test_register_rejects_invalid_email(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/register", json={"email": "not-an-email", "password": "red123456"})
    assert resp.status_code == 400


def test_register_rejects_short_password(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/register", json={"email": "short@xian.local", "password": "123"})
    assert resp.status_code == 422


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    payload = {"email": "dup@xian.local", "password": "dup123456", "role": "blue"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    again = client.post("/api/v1/auth/register", json=payload)
    assert again.status_code == 409


def test_login_verifies_registered_password(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "verify@xian.local", "password": "correct-horse", "role": "analyst"},
    )
    ok = client.post("/api/v1/auth/login", json={"email": "verify@xian.local", "password": "correct-horse"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["role"] == "analyst"

    bad = client.post("/api/v1/auth/login", json={"email": "verify@xian.local", "password": "wrong-pass"})
    assert bad.status_code == 401


def test_login_keeps_dev_fallback_for_unknown_account(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/login", json={"email": "demo@xian.local", "password": "anything"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "blue"