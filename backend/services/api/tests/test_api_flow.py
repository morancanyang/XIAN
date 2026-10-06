"""端到端 API 契约测试：接入 → 归属 → 战役 → 记录 → 报告 → 门禁。

覆盖 AC-01/02/05/07/09/11 的 HTTP 层片段，使用 SQLite 内存库与离线 LLM 回放。
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
        "X-Tenant-Id": "11111111-1111-1111-1111-111111111111",
        "X-User-Id": "22222222-2222-2222-2222-222222222222",
        "X-Role": "admin",
    }


def _create_agent(client: TestClient, headers: dict[str, str]) -> str:
    payload = {
        "name": "客服 Agent",
        "endpoint": "http://127.0.0.1:9000/v1/chat",
        "access_type": "http",
        "system_prompt": "你是电商客服助手",
        "tools": [{"name": "query_order", "scope": "read"}],
        "owner": "alice@corp.com",
        "scenario_id": "S1",
    }
    resp = client.post("/api/v1/agents", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _verify_ownership(client: TestClient, headers: dict[str, str], agent_id: str) -> None:
    resp = client.post(
        f"/api/v1/agents/{agent_id}/verify",
        json={"method": "dns_txt", "target": "agent-a.corp.com"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    nonce = resp.json()["nonce"]
    os.environ["XIAN_VERIFY_TXT"] = f"agent-a.corp.com=xian-verify={nonce}"
    resp = client.post(
        f"/api/v1/agents/{agent_id}/verify",
        json={"method": "dns_txt", "target": "agent-a.corp.com"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "verified", resp.text


def test_health_and_ready(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200


def test_access_requires_permission(client: TestClient, headers: dict[str, str]) -> None:
    """viewer 不能写 Agent（RBAC 生效）。"""
    viewer = dict(headers, **{"X-User-Id": str(uuid4()), "X-Role": "viewer"})
    resp = client.post("/api/v1/agents", json={"name": "x", "endpoint": "http://x", "access_type": "http"}, headers=viewer)
    assert resp.status_code == 403
    assert "无权" in resp.json()["detail"]


def test_unowned_agent_blocks_campaign(client: TestClient, headers: dict[str, str]) -> None:
    """AC-09 前半：未归属 Agent 阻断演练。"""
    agent_id = _create_agent(client, headers)
    resp = client.post(
        "/api/v1/campaigns",
        json={"agent_id": agent_id, "scope": ["XM-01"], "budget": {"token": 5000, "cases": 3, "minutes": 5}},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


def test_full_mode_one_flow(client: TestClient, headers: dict[str, str]) -> None:
    """AC-01/05/07：接入 → 战役 → 记录 → 报告 → 导出 全链路。"""
    agent_id = _create_agent(client, headers)
    _verify_ownership(client, headers, agent_id)

    resp = client.post(f"/api/v1/agents/{agent_id}/healthcheck", headers=headers)
    assert resp.status_code == 200 and resp.json()["result"] == "ok"

    resp = client.post(
        "/api/v1/campaigns",
        json={
            "agent_id": agent_id,
            "scope": ["XM-01", "XM-04"],
            "intensity": "standard",
            "budget": {"token": 20000, "cases": 4, "minutes": 10},
            "constraints": {"max_turns": 2},
            "judge_mode": "standard",
            "output_mode": "full",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    campaign_id = resp.json()["id"]
    assert resp.json()["status"] == "draft"

    resp = client.post(f"/api/v1/campaigns/{campaign_id}/run", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] in {"completed", "running"}
    if body["status"] == "completed":
        assert body["result"]["executed"] >= 1

    resp = client.get(f"/api/v1/campaigns/{campaign_id}/records", headers=headers)
    assert resp.status_code == 200
    records = resp.json()["items"]
    assert records, "战役应产生攻击记录"
    first = records[0]

    trace = client.get(f"/api/v1/records/{first['id']}/trace", headers=headers)
    assert trace.status_code == 200
    assert trace.json()["events"], "trace 应可回放"

    report = client.post(f"/api/v1/reports/campaigns/{campaign_id}", headers=headers)
    assert report.status_code == 200, report.text
    report_id = report.json()["id"]
    assert 0 <= report.json()["sec_score"] <= 100

    exported = client.post(
        f"/api/v1/reports/{report_id}/export",
        json={"formats": ["html", "json"], "desensitize_level": "standard"},
        headers=headers,
    )
    assert exported.status_code == 200, exported.text
    formats = {a["format"] for a in exported.json()["artifacts"]}
    assert {"html", "json"} <= formats

    detail = client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert detail.status_code == 200 and detail.json()["chapters"]


def test_campaign_state_machine_rejects_invalid_transition(client: TestClient, headers: dict[str, str]) -> None:
    agent_id = _create_agent(client, headers)
    _verify_ownership(client, headers, agent_id)
    resp = client.post(
        "/api/v1/campaigns",
        json={"agent_id": agent_id, "scope": ["XM-01"], "budget": {"token": 5000, "cases": 3, "minutes": 5}},
        headers=headers,
    )
    campaign_id = resp.json()["id"]
    bad = client.patch(f"/api/v1/campaigns/{campaign_id}", json={"status": "completed"}, headers=headers)
    assert bad.status_code == 409


def test_weapon_export_blocked_for_red_role(client: TestClient, headers: dict[str, str]) -> None:
    """AC-09 后半：武器库越权导出拦截。"""
    red = dict(headers, **{"X-User-Id": str(uuid4()), "X-Role": "red"})
    resp = client.get("/api/v1/matrix/cases", headers=red)
    assert resp.status_code == 200
    case = resp.json()[0]
    export = client.get(f"/api/v1/matrix/cases/{case['id']}/export", headers=red)
    assert export.status_code == 403


def test_ten_levels_open_and_submit(client: TestClient, headers: dict[str, str]) -> None:
    levels = client.get("/api/v1/levels", headers=headers).json()
    assert len(levels) == 10
    assert [lv["id"] for lv in levels] == [f"L{i}" for i in range(1, 11)]

    assert client.post("/api/v1/levels/L1/start", headers=headers).status_code == 201
    locked = client.post("/api/v1/levels/L2/submit", json={"output": "x"}, headers=headers)
    assert locked.status_code == 404

    hint = client.post("/api/v1/levels/L1/hint", json={"hint_level": "H1"}, headers=headers)
    assert hint.status_code == 200
    assert hint.json()["energy_cost"] == 10

    submitted = client.post(
        "/api/v1/levels/L1/submit",
        json={
            "system_prompt": "secret_instruction value_alpha value_beta",
            "output": "there are secret_instruction and value_alpha",
        },
        headers=headers,
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "passed"

    assert client.post("/api/v1/levels/L2/start", headers=headers).status_code == 201

    hardening = client.get("/api/v1/levels/L1/hardening", headers=headers)
    assert hardening.status_code == 200


def test_campaign_plan_dag_aligns_with_commander(client: TestClient, headers: dict[str, str]) -> None:
    """回归：plan_campaign 必须按 commander.build_plan 的真实签名构造 DAG。"""
    agent_id = _create_agent(client, headers)
    _verify_ownership(client, headers, agent_id)
    resp = client.post(
        "/api/v1/campaigns",
        json={"agent_id": agent_id, "scope": ["XM-01", "XM-03"], "intensity": "standard"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    plan = client.post(f"/api/v1/campaigns/{resp.json()['id']}/plan", headers=headers)
    assert plan.status_code == 200, plan.text
    body = plan.json()
    codes = sorted(node["category_code"] for node in body["dag_nodes"])
    assert codes == ["XM-01", "XM-03"], codes
    assert set(body["budget_split"]) == set(codes)
