"""Agent 资产列表的状态过滤。

``list_agents`` 原先写死只返回 ``status == "active"``，刚接入、尚未完成归属校验的
资产在列表和各处 Agent 选择器里直接消失——前端状态筛选UI（默认 all）因此永远只能
看到 active，选"未验证"必然是空列表。
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


@pytest.fixture()
def headers() -> dict[str, str]:
    return {
        "X-Tenant-Id": str(uuid4()),
        "X-User-Id": str(uuid4()),
        "X-Role": "admin",
    }


def _create_agent(client: TestClient, headers: dict[str, str], name: str, endpoint: str = "http://x") -> dict:
    resp = client.post(
        "/api/v1/agents",
        json={"name": name, "access_type": "http", "endpoint": endpoint},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_default_listing_includes_unverified_agents(client: TestClient, headers: dict[str, str]) -> None:
    """缺省不再过滤掉未校验资产：接入向导第一步建完的资产必须立刻可见、可选中。"""
    agent = _create_agent(client, headers, "刚接入还没校验")
    assert agent["status"] == "unverified"

    items = client.get("/api/v1/agents", headers=headers).json()["items"]
    assert any(a["id"] == agent["id"] for a in items)


def test_status_query_filters_server_side(client: TestClient, headers: dict[str, str]) -> None:
    """状态筛选由服务端执行，翻页后依然准确（客户端过滤只作用于当前页）。"""
    agent = _create_agent(client, headers, "待过滤")

    unverified = client.get("/api/v1/agents", params={"status": "unverified"}, headers=headers).json()
    assert [a["id"] for a in unverified["items"]] == [agent["id"]]
    assert unverified["total"] == 1

    active = client.get("/api/v1/agents", params={"status": "active"}, headers=headers).json()
    assert active["items"] == []
    assert active["total"] == 0


def test_unknown_status_is_rejected(client: TestClient, headers: dict[str, str]) -> None:
    """非法状态值必须 422，不能静默返回空列表把人误导成"没有资产"。"""
    resp = client.get("/api/v1/agents", params={"status": "bogus"}, headers=headers)
    assert resp.status_code == 422


def test_keyword_searches_name_and_endpoint(client: TestClient, headers: dict[str, str]) -> None:
    """关键字要命中名称与端点（前端搜索框的提示就是"搜索名称 / 端点"）。"""
    by_name = _create_agent(client, headers, "订单客服 Agent")
    by_endpoint = _create_agent(client, headers, "另一个", endpoint="http://orders.internal/chat")

    hit_name = client.get("/api/v1/agents", params={"keyword": "订单客服"}, headers=headers).json()
    assert [a["id"] for a in hit_name["items"]] == [by_name["id"]]

    hit_endpoint = client.get("/api/v1/agents", params={"keyword": "orders.internal"}, headers=headers).json()
    assert [a["id"] for a in hit_endpoint["items"]] == [by_endpoint["id"]]


def test_keyword_is_case_insensitive(client: TestClient, headers: dict[str, str]) -> None:
    agent = _create_agent(client, headers, "Payment Bot", endpoint="http://x")
    body = client.get("/api/v1/agents", params={"keyword": "payment"}, headers=headers).json()
    assert [a["id"] for a in body["items"]] == [agent["id"]]


def test_keyword_combines_with_status(client: TestClient, headers: dict[str, str]) -> None:
    agent = _create_agent(client, headers, "组合筛选探针")
    body = client.get(
        "/api/v1/agents", params={"keyword": "组合筛选", "status": "unverified"}, headers=headers
    ).json()
    assert [a["id"] for a in body["items"]] == [agent["id"]]

    miss = client.get(
        "/api/v1/agents", params={"keyword": "组合筛选", "status": "active"}, headers=headers
    ).json()
    assert miss["items"] == []


def test_keyword_without_match_returns_empty(client: TestClient, headers: dict[str, str]) -> None:
    _create_agent(client, headers, "存在但搜不到")
    body = client.get("/api/v1/agents", params={"keyword": "绝不存在的关键词"}, headers=headers).json()
    assert body["items"] == []
    assert body["total"] == 0
