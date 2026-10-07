"""场景市场与实例化契约测试。

背景：实例化一直报 HTTP 422 —— `InstanceCreate.scenario_id` 声明成 UUID，
而场景市场对外暴露的 id 是模板编码（S1/S2），前端把编码原样传上来必然被拦。
同时 `GET /scenarios/instances` 注册在 `GET /scenarios/{code}` 之后，
被 `code="instances"` 抢先匹配，"已有实例 N 个"永远拿不到数据。
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


def test_market_exposes_template_code_as_id(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/scenarios", headers=headers)
    assert resp.status_code == 200
    first = resp.json()[0]
    assert first["id"] == "S1"


def test_instantiate_accepts_scenario_code(client: TestClient, headers: dict[str, str]) -> None:
    """回归：实例化入参必须是场景编码，UUID 类型声明会让正常请求直接 422。"""
    resp = client.post(
        "/api/v1/scenarios/instances",
        json={"scenario_id": "S1", "data_scale": 10, "canary_enhanced": True, "run_baseline": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] in {"ready", "provisioning"}
    assert body["seed_data_snapshot"], "应带种子数据快照"


def test_instantiate_unknown_scenario_returns_404(client: TestClient, headers: dict[str, str]) -> None:
    """未知场景应给出可读的 404，而不是 KeyError 500。"""
    resp = client.post(
        "/api/v1/scenarios/instances",
        json={"scenario_id": "S999", "data_scale": 10},
        headers=headers,
    )
    assert resp.status_code == 404, resp.text


def test_list_instances_not_swallowed_by_code_route(client: TestClient, headers: dict[str, str]) -> None:
    """回归：静态段 /instances 必须早于 /{code} 注册，否则被 code=instances 抢走。"""
    resp = client.get("/api/v1/scenarios/instances", headers=headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)