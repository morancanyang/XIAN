"""大模型接入 API：状态 / 供应商预设 / 探测 / 热更新（技术方案 7.2）。

不访问真实供应商：探测与补全都用假传输层替换，因此恒为离线断言。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
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


def test_healthz_reports_llm_offline(client: TestClient) -> None:
    body = client.get("/healthz").json()
    assert body["status"] == "ok"
    assert body["llm"] == {"configured": False, "offline": True, "provider": "custom"}


def test_llm_status_is_offline_with_masked_key(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/llm/status", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is False
    assert body["offline"] is True
    assert set(body["models"]) == {"redteam", "target", "judge", "embedding"}
    assert body["api_key"] == ""  # 未配置时不应回显任何 Key 片段


def test_llm_providers_lists_presets(client: TestClient, headers: dict[str, str]) -> None:
    names = {p["name"] for p in client.get("/api/v1/llm/providers", headers=headers).json()["providers"]}
    assert {"deepseek", "dashscope", "openai"} <= names


def test_llm_probe_reports_not_configured(client: TestClient, headers: dict[str, str]) -> None:
    body = client.post("/api/v1/llm/probe", headers=headers).json()
    assert body["ok"] is False
    assert "未配置" in body["detail"]


def test_llm_config_hot_swaps_endpoint(client: TestClient, headers: dict[str, str], monkeypatch) -> None:
    """热更新后网关立即按新端点工作，探测用假传输层，不会真的发请求。"""
    from xian_core.llm.gateway import gateway
    from xian_core.llm.transport import OpenAICompatTransport, ProbeResult

    async def _fake_probe(self):
        return ProbeResult(True, 12, "端点可用", ("deepseek-chat",))

    monkeypatch.setattr(OpenAICompatTransport, "probe", _fake_probe)
    body = client.post(
        "/api/v1/llm/config",
        headers=headers,
        json={
            "provider": "deepseek",
            "api_key": "sk-fake-1234567890",
            "judge_model": "deepseek-reasoner",
        },
    ).json()
    assert body["configured"] is True
    assert body["provider"] == "deepseek"
    assert body["base_url"] == "https://api.deepseek.com/v1"
    assert body["models"]["judge"] == "deepseek-reasoner"
    assert body["probe"] == {"ok": True, "latency_ms": 12, "detail": "端点可用"}
    # Key 只回显打码结果，不明文落进响应
    assert "sk-fake-1234567890" not in str(body)

    # 复原，避免污染同会话内的其它用例
    gateway.configure(base_url="", api_key="")