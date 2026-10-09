"""红蓝对抗客户端适配：把基础设施（LLM 网关 / 沙箱）适配为攻防引擎需要的协议。

只有这里知道"怎么把消息发给目标"：SDK 注入走 HTTP 直连，容器镜像走沙箱内 sidecar，
mock 环境走 :class:`xian_core.sandbox.mock_runtime.MockRuntime`。
"""

from __future__ import annotations

import time
from typing import Any, Protocol


def _is_loopback(url: str) -> bool:
    """回环地址不应走代理：本机常配有本地代理（如 127.0.0.1:6518），直连会被 502 拒绝。"""
    from urllib.parse import urlsplit

    host = (urlsplit(url).hostname or "").lower()
    return host in ("localhost", "0.0.0.0", "::1") or host.startswith("127.")


def resolve_agent_client(agent: Any) -> Any:
    """按 Agent 资产的接入方式挑客户端：HTTP/SDK 直连端点，其余回退 LLM 网关（离线可回放）。

    模式一战役与模式二自由攻击共用同一套判定，目标调用方式也必须一致，
    否则战役永远走离线回显、跑得飞快却没有任何真实观测。
    """
    from ..llm.gateway import gateway

    endpoint = str(getattr(agent, "endpoint", "") or "").strip()
    access_type = str(getattr(agent, "access_type", "") or "").lower()
    if endpoint and access_type in ("http", "sdk"):
        return HttpChatClient(endpoint)
    return GatewayChatClient(gateway)


class ChatClient(Protocol):
    """AgentClient 协议（xian_core.redteam.recon.AgentClient）。"""

    async def chat(self, message: str, *, session_id: str | None = None) -> dict[str, Any]:
        ...


class GatewayChatClient:
    """经 LLMGateway 调用目标模型（OpenAI 兼容端点直连）。"""

    def __init__(self, gateway: Any, *, role: str = "target", system: str = "") -> None:
        self._gateway = gateway
        self._role = role
        self._system = system

    async def chat(self, message: str, *, session_id: str | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        response = await self._gateway.complete(message, role=self._role, system=self._system)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "output": getattr(response, "text", "") or "",
            "events": [],
            "latency_ms": getattr(response, "latency_ms", latency_ms),
            "tokens": int(getattr(response, "total_tokens", 0) or 0),
            "session_id": session_id,
        }


class SandboxChatClient:
    """经沙箱实例调用目标 Agent（容器镜像接入方式）。"""

    def __init__(self, runtime: Any, instance_id: str, *, tool: str = "agent_chat") -> None:
        self._runtime = runtime
        self._instance_id = instance_id
        self._tool = tool

    async def chat(self, message: str, *, session_id: str | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        result = self._runtime.execute_tool(self._instance_id, self._tool, {"message": message})
        latency_ms = int((time.perf_counter() - started) * 1000)
        # 观测事件由运行时给出（蜜标命中 + 无护栏目标的工具调用），这里只做搬运。
        # 原先写死成「有 canary_hit 才给一条事件」，靶场顺从载荷产生的 tool_call
        # 全被丢在半路，裁判只能看到一句回显。
        events = list(result.get("events") or [])
        if result.get("canary_hit") and not any(e.get("type") == "canary_hit" for e in events):
            events.append({"type": "canary_hit", "via": "egress"})
        return {
            "output": str(result.get("result", "")),
            "events": events,
            "latency_ms": latency_ms,
            "tokens": 0,
            "session_id": session_id,
        }


class HttpChatClient:
    """HTTP / SDK 接入的目标 Agent：按 ChatClient 协议直连端点（PRD 3.2.4）。"""

    def __init__(self, endpoint: str, *, timeout_s: float = 30.0) -> None:
        self._url = str(endpoint or "").strip()
        self._timeout_s = timeout_s

    async def chat(self, message: str, *, session_id: str | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        import httpx

        # 回环目标禁用环境代理，其余目标保留（公司内网可能需要代理出网）
        async with httpx.AsyncClient(timeout=self._timeout_s, trust_env=not _is_loopback(self._url)) as client:
            resp = await client.post(self._url, json={"message": message, "session_id": session_id or ""})
            resp.raise_for_status()
            data = resp.json()
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "output": str(data.get("output", "") or ""),
            "events": list(data.get("events", []) or []),
            "latency_ms": int(data.get("latency_ms", 0) or latency_ms),
            "tokens": int(data.get("tokens", 0) or 0),
            "session_id": session_id or str(data.get("session_id", "") or ""),
        }
