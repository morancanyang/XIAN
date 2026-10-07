# -*- coding: utf-8 -*-
"""回归：两个曾因字段/参数名不匹配而 500 的只读接口。

- admin/audit-logs：Repository.list() 只接受 limit，调用方传了 size，直接 TypeError
- profile/achievements：ACHIEVEMENTS 内容资产字段叫 code，契约 AchievementOut 要 id
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


@pytest.fixture()
def headers() -> dict[str, str]:
    return {
        "X-Tenant-Id": "11111111-1111-1111-1111-111111111111",
        "X-User-Id": "22222222-2222-2222-2222-222222222222",
        "X-Role": "admin",
    }


def test_achievements_contract_matches_catalog(client: TestClient, headers: dict[str, str]) -> None:
    """契约字段是 id；内容资产用 code，路由必须显式映射而不是直接 ** 展开。"""
    from xian_core.levels import achievement_catalog
    from xian_core.schemas.level import AchievementOut

    catalog = achievement_catalog()
    assert catalog, "成就目录不能为空"
    assert all("code" in a and "id" not in a for a in catalog)

    resp = client.get("/api/v1/profile/achievements", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == len(catalog)
    for row, source in zip(body, catalog):
        assert row["id"] == source["code"]
        assert row["name"] == source["name"]
        assert row["condition"] == source["condition"]
        assert row["rarity"] == source["rarity"]
        AchievementOut.model_validate(row)


def test_audit_logs_accepts_limit(client: TestClient, headers: dict[str, str]) -> None:
    """list() 的入参名是 limit 而不是 size；空库时返回空列表即可。"""
    resp = client.get("/api/v1/admin/audit-logs", params={"limit": 10}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)
    assert len(resp.json()) <= 10


def test_repository_list_rejects_size_kwarg() -> None:
    """静态契约：Repository.list 没有 size 形参，调用方不得再传。"""
    from inspect import signature

    from xian_core.db.repositories import Repository

    params = signature(Repository.list).parameters
    assert "limit" in params
    assert "size" not in params
