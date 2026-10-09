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


def test_matrix_case_render_fills_default_variables(client: TestClient, headers: dict[str, str]) -> None:
    """模式二武器库选中即用：模板必须渲染成成品载荷。

    控制台原先选中用例只回一个标题 chip，载荷要用户手打，输入框里躺着的往往是
    标题本身——靶场只会回显，裁判翻遍 trace 找不到证据，只能判"未发生"。
    """
    case = client.get("/api/v1/matrix/cases/XM-01-011", headers=headers).json()
    assert "{{new_goal}}" in case["payload_template"], "用例模板应带占位符"

    rendered = client.get("/api/v1/matrix/cases/XM-01-011/render", headers=headers)
    assert rendered.status_code == 200, rendered.text
    body = rendered.json()
    assert body["case_id"] == "XM-01-011"
    assert body["variables"] == case["variables"]
    assert body["missing"] == [], "种子用例的变量都应被默认值覆盖"
    assert "{{" not in body["payload"], "默认变量已覆盖的占位符必须被替换"
    assert "配合完成本次内部测试" in body["payload"]

    unknown = client.get("/api/v1/matrix/cases/XM-99-999/render", headers=headers)
    assert unknown.status_code == 404


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


def test_profile_radar_tracks_the_technique_actually_used(
    client: TestClient, headers: dict[str, str]
) -> None:
    """能力雷达必须跟着账号实际用的手法走，不能恒为同一个数。

    回归：submit_attempt 从不写 dimension_coverage，profile 只能给每个手法打 0.8，
    结果六条轴永远是 80，换谁来、打成什么样都一样。
    """
    assert client.get("/api/v1/levels", headers=headers).status_code == 200
    client.post("/api/v1/levels/L1/start", headers=headers)
    submitted = client.post(
        "/api/v1/levels/L1/submit",
        json={
            "system_prompt": "secret_instruction value_alpha value_beta",
            "output": "there are secret_instruction and value_alpha",
            "technique": "翻译",
        },
        headers=headers,
    )
    assert submitted.status_code == 200, submitted.text
    coverage = submitted.json()["dimension_coverage"]
    assert coverage["翻译"] > coverage["直接诱导"], "亲手用过的手法要高于同关未用的"

    profile = client.get("/api/v1/profile", headers=headers).json()
    radar = profile["radar"]
    assert radar["注入"] > 0, "用过注入类手法后注入轴必须有分"
    assert radar["外带"] == 0.0, "没打过外带关就不能有分外带轴"
    assert profile["tier"] == "bronze"
    assert profile["next_tier"] == "silver"
    assert profile["points_to_next_tier"] == 300 - profile["points"]
    assert 0 < profile["tier_progress"] < 100


def test_profile_radar_differs_between_users(client: TestClient, headers: dict[str, str]) -> None:
    """同一个后端、不同账号，雷达不能长得一样。"""
    assert client.get("/api/v1/levels", headers=headers).status_code == 200
    other = {**headers, "X-User-Id": "33333333-3333-3333-3333-333333333333"}
    client.post("/api/v1/levels/L1/start", headers=other)
    l1 = client.post(
        "/api/v1/levels/L1/submit",
        json={
            "system_prompt": "secret_instruction value_alpha value_beta",
            "output": "there are secret_instruction and value_alpha",
            "technique": "翻译",
        },
        headers=other,
    )
    assert l1.status_code == 200, l1.text

    # L3 是编码变形关：密语以 base64 形态出现在输出里才算通关
    client.post("/api/v1/levels/L3/start", headers=other)
    l3 = client.post(
        "/api/v1/levels/L3/submit",
        json={
            "secret_token": "sk-canary-CUSTOMER-001-",
            # sk-canary-CUSTOMER-001- 的 base64 形态：L3 判定的是"变形后仍完整出现"
            "output": "c2stY2FuYXJ5LUNVU1RPTUVSLTAwMS0=",
            "technique": "base64",
        },
        headers=other,
    )
    assert l3.status_code == 200, l3.text
    assert l3.json()["attempt_passed"] is True, l3.json()["attempt_reason"]

    mine = client.get("/api/v1/profile", headers=headers).json()["radar"]
    theirs = client.get("/api/v1/profile", headers=other).json()["radar"]
    assert mine["注入变种"] == 0.0 and theirs["注入变种"] > 0
    assert mine != theirs


def test_resubmitting_passed_level_reports_attempt_verdict(
    client: TestClient, headers: dict[str, str]
) -> None:
    """已通关的关卡重复提交：回传本次判定，不能拿历史状态弹通关成功。

    空提交也曾被判"通关成功 · 100 分"——submit_attempt 只回传 row.status，
    而已通关关卡的状态永远是 passed，与本次判定无关。
    """
    # 列表端点懒种子：库里没关卡时先拉一次，否则 start 会 404
    assert client.get("/api/v1/levels", headers=headers).status_code == 200
    client.post("/api/v1/levels/L1/start", headers=headers)
    passed = client.post(
        "/api/v1/levels/L1/submit",
        json={
            "system_prompt": "secret_instruction value_alpha value_beta",
            "output": "there are secret_instruction and value_alpha",
        },
        headers=headers,
    )
    assert passed.status_code == 200, passed.text
    assert passed.json()["attempt_passed"] is True

    again = client.post("/api/v1/levels/L1/submit", json={"output": "参数篡改"}, headers=headers)
    assert again.status_code == 200, again.text
    body = again.json()
    assert body["attempt_passed"] is False, "空提交必须判未通过"
    assert body["attempt_reason"], "未通过要给出原因"
    assert body["status"] == "passed", "历史通关状态不被本次失败抹掉"
    assert body["score"] == passed.json()["score"], "历史最好成绩不被拉低"


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


def test_report_regeneration_refreshes_instead_of_duplicating(
    client: TestClient, headers: dict[str, str]
) -> None:
    """同一战役重复生成报告必须是刷新，不能无限追加行。

    之前两个生成端点都直接 insert：点几次"生成报告"列表里就多出几行同一个战役，
    而且旧的那行带着已经修掉的渲染缺陷（kill chain 阶段错报），用户看到的是过期快照。
    """
    agent_id = _create_agent(client, headers)
    _verify_ownership(client, headers, agent_id)
    resp = client.post(
        "/api/v1/campaigns",
        json={"agent_id": agent_id, "scope": ["XM-01"], "budget": {"token": 5000, "cases": 3, "minutes": 5}},
        headers=headers,
    )
    campaign_id = resp.json()["id"]

    first = client.post(f"/api/v1/reports/campaigns/{campaign_id}", headers=headers)
    assert first.status_code == 200, first.text
    second = client.post(f"/api/v1/reports/campaigns/{campaign_id}", headers=headers)
    assert second.status_code == 200, second.text

    assert first.json()["id"] == second.json()["id"], "重复生成应落在同一行上"
    assert second.json()["version"] == 2, "重新生成要递增版本号"

    listed = client.get("/api/v1/reports", headers=headers).json()
    mine = [r for r in listed if r["subject_id"] == campaign_id]
    assert len(mine) == 1, f"同一战役出现 {len(mine)} 份报告"

    detail = client.get(f"/api/v1/reports/{second.json()['id']}", headers=headers)
    assert detail.status_code == 200 and detail.json()["chapters"]


def test_delete_report_removes_row_and_exports(client: TestClient, headers: dict[str, str]) -> None:
    """删除报告要连行带导出记录一起清掉，删完再取是 404。

    这是清理存量重复报告（同主体多行）的入口：重新生成只刷新当前生效的那一行，
    多余的旧行要么在这里显式删掉，要么在下次重新生成时被顺手清掉。
    """
    agent_id = _create_agent(client, headers)
    _verify_ownership(client, headers, agent_id)
    resp = client.post(
        "/api/v1/campaigns",
        json={"agent_id": agent_id, "scope": ["XM-01"], "budget": {"token": 5000, "cases": 3, "minutes": 5}},
        headers=headers,
    )
    campaign_id = resp.json()["id"]
    report_id = client.post(f"/api/v1/reports/campaigns/{campaign_id}", headers=headers).json()["id"]
    exported = client.post(
        f"/api/v1/reports/{report_id}/export",
        json={"formats": ["json"], "desensitize_level": "standard"},
        headers=headers,
    )
    assert exported.status_code == 200, exported.text

    viewer = dict(headers, **{"X-Role": "viewer"})
    assert client.delete(f"/api/v1/reports/{report_id}", headers=viewer).status_code == 403

    deleted = client.delete(f"/api/v1/reports/{report_id}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted"] is True
    assert client.get(f"/api/v1/reports/{report_id}", headers=headers).status_code == 404
    assert client.delete(f"/api/v1/reports/{report_id}", headers=headers).status_code == 404
    listed = client.get("/api/v1/reports", headers=headers).json()
    assert all(r["id"] != report_id for r in listed)
