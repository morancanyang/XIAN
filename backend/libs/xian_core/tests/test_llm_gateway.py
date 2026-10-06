"""LLM 网关：接入配置推断 / 传输层归一化 / 熔断降级（技术方案 7.2）。

不访问真实供应商：用假端点与 monkeypatch 出来的 httpx 客户端驱动。
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from xian_core.config import PROVIDER_PRESETS, LLMSettings, resolve_provider
from xian_core.errors import LLMProviderError
from xian_core.llm.gateway import LLMGateway
from xian_core.llm.transport import OpenAICompatTransport, is_loopback, normalize_base_url


# ------------------------------------------------------------------ 配置推断


def test_resolve_provider_prefers_explicit_name() -> None:
    assert resolve_provider("deepseek", "https://api.moonshot.cn", "") == "deepseek"


def test_resolve_provider_matches_base_url() -> None:
    assert resolve_provider("", "https://api.siliconflow.cn/v1", "") == "siliconflow"


def test_resolve_provider_unknown_stays_blank() -> None:
    assert resolve_provider("", "https://my-gateway.internal/v1", "sk-x") == ""


def test_empty_settings_are_offline() -> None:
    """显式置空的配置不能被 Key 环境变量反推覆盖，否则测试环境无法保证离线。"""
    cfg = LLMSettings(provider="", base_url="", api_key="")
    assert cfg.ready is False


def test_preset_fills_models_and_endpoint() -> None:
    cfg = LLMSettings(provider="dashscope", api_key="sk-test")
    assert cfg.ready is True
    assert cfg.base_url == PROVIDER_PRESETS["dashscope"]["base_url"]
    assert cfg.redteam_model == "qwen-plus"
    # 未显式指定次级裁判模型时，与主裁判一致，避免空 model 打到供应商
    assert cfg.judge_model_secondary == cfg.judge_model


# ------------------------------------------------------------------ 传输层


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://api.deepseek.com", "https://api.deepseek.com/v1"),
        ("https://api.deepseek.com/v1/", "https://api.deepseek.com/v1"),
        ("http://127.0.0.1:4000", "http://127.0.0.1:4000/v1"),
        ("https://open.bigmodel.cn/api/paas/v4", "https://open.bigmodel.cn/api/paas/v4"),
        ("", ""),
    ],
)
def test_normalize_base_url(raw: str, expected: str) -> None:
    assert normalize_base_url(raw) == expected


def test_is_loopback_bypasses_proxy() -> None:
    assert is_loopback("http://127.0.0.1:4000/v1") is True
    assert is_loopback("http://localhost:11434/v1") is True
    assert is_loopback("https://api.deepseek.com/v1") is False


def test_transport_unconfigured_without_key() -> None:
    transport = OpenAICompatTransport(base_url="https://api.deepseek.com", api_key="")
    assert transport.configured is False


def _json_response(payload: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload, request=httpx.Request("POST", "https://fake.local/v1/x"))


def test_chat_parses_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = OpenAICompatTransport(base_url="https://fake.local", api_key="sk-x", max_retries=0)
    captured: dict = {}

    class _FakeClient:
        def post(self, path, json):  # noqa: A002 - 与 httpx 形参同名
            captured["path"] = path
            captured["payload"] = json
            return asyncio.sleep(0, _json_response({
                "model": "deepseek-chat",
                "choices": [{"message": {"content": "pong"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            }))

    monkeypatch.setattr(OpenAICompatTransport, "_http", lambda self: _FakeClient())
    result = asyncio.run(transport.chat([{"role": "user", "content": "ping"}], model="deepseek-chat"))
    assert result.text == "pong"
    assert result.total_tokens == 10
    assert captured["path"] == "/chat/completions"
    assert captured["payload"]["stream"] is False


def test_chat_raises_readable_error_on_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = OpenAICompatTransport(base_url="https://fake.local", api_key="bad", max_retries=0)

    class _FakeClient:
        def post(self, path, json):  # noqa: A002
            return asyncio.sleep(
                0,
                httpx.Response(
                    401,
                    json={"error": "invalid api key"},
                    request=httpx.Request("POST", "https://fake.local/v1/x"),
                ),
            )

    monkeypatch.setattr(OpenAICompatTransport, "_http", lambda self: _FakeClient())
    with pytest.raises(LLMProviderError) as excinfo:
        asyncio.run(transport.chat([{"role": "user", "content": "ping"}], model="m"))
    assert "401" in str(excinfo.value)


def test_probe_reports_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = OpenAICompatTransport(base_url="https://fake.local", api_key="sk-x")

    def _boom(_self, _path):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(httpx.AsyncClient, "get", _boom)
    result = asyncio.run(transport.probe())
    assert result.ok is False
    assert result.latency_ms >= 0


# ------------------------------------------------------------------ 网关熔断


def test_gateway_falls_back_to_offline_after_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """连续失败达到阈值后熔断，之后不再打端点，直接走离线回放。"""
    gw = LLMGateway()
    monkeypatch.setattr(gw, "_build_transport", lambda: OpenAICompatTransport(
        base_url="https://fake.local", api_key="sk-x", max_retries=0
    ))
    calls = {"n": 0}

    class _FailingClient:
        def post(self, path, json):  # noqa: A002
            calls["n"] += 1
            return asyncio.sleep(
                0,
                httpx.Response(
                    500, json={}, request=httpx.Request("POST", "https://fake.local/v1/x")
                ),
            )

    async def _run() -> list:
        out = []
        for _ in range(5):
            resp = await gw.complete("hi", role="judge")
            out.append(resp.degraded)
        return out

    monkeypatch.setattr(OpenAICompatTransport, "_http", lambda self: _FailingClient())
    asyncio.run(_run())
    assert calls["n"] == 3, "熔断后不应继续请求供应商"
    assert gw.offline is True
    assert gw.status()["circuit_open"] is True


def test_gateway_offline_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    gw = LLMGateway()
    monkeypatch.setattr(gw, "_build_transport", lambda: OpenAICompatTransport(base_url="", api_key=""))
    assert gw.transport is None
    assert gw.offline is True
    resp = asyncio.run(gw.complete("hi", role="judge"))
    assert resp.degraded is True
    assert "offline::" in resp.model


def test_gateway_status_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    gw = LLMGateway()
    monkeypatch.setattr(gw, "_build_transport", lambda: OpenAICompatTransport(
        base_url="https://fake.local", api_key="sk-x", max_retries=0
    ))
    status = gw.status()
    assert status["configured"] is True
    assert set(status["models"]) == {"redteam", "target", "judge", "embedding"}
    assert status["online_calls"] == 0