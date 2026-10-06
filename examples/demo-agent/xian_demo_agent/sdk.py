"""SDK 接入方式：平台在运行期持有 chat 回调，无需 Agent 暴露 HTTP 端口。

对齐 ``xian_core.redteam.clients.ChatClient.chat`` 协议，
使平台 ``resolve_client()`` 能在 HTTP 网关 / SDK 回调 / 沙箱 sidecar 之间无差别切换。
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any

from .core import CANARY_TOKEN, build_chat_response

DEFAULT_TIMEOUT = 10.0


class SDKError(RuntimeError):
    """SDK 接入过程中的失败（网络 / 协议 / 归属未校验）。"""


@dataclass(slots=True)
class SDKHandle:
    """平台侧持有的客户端句柄，取消注册后立即失效。"""

    agent_id: str
    client: DemoAgentSDK
    registered_at: float = field(default_factory=time.time)
    _closed: bool = field(default=False, init=False)

    def unregister(self) -> None:
        if not self._closed:
            self.client.close()
            self._closed = True


class DemoAgentSDK:
    """零依赖 SDK 客户端。

    - ``endpoint=""``：离线模式，直接在进程内构造响应（默认，用于 CI 自检）；
    - ``endpoint="http://host:port"``：联机模式，指向 ``python -m xian_demo_agent.server``。
    """

    def __init__(self, *, endpoint: str = "", token: str = "", timeout: float = DEFAULT_TIMEOUT) -> None:
        import os

        self.endpoint = (endpoint or os.environ.get("XIAN_DEMO_ENDPOINT", "")).rstrip("/")
        self.token = token or CANARY_TOKEN
        self.timeout = timeout
        self._session_id = f"sdk-{uuid.uuid4().hex[:12]}"

    # ----------------------------------------------------------- protocol
    def chat(self, message: str, *, session_id: str | None = None) -> dict[str, Any]:
        """与 ``ChatClient.chat`` 同构。"""
        sid = session_id or self._session_id
        if not self.endpoint:
            return build_chat_response(message, sid)

        payload = json.dumps({"message": message, "session_id": sid}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.endpoint}/chat",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise SDKError(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise SDKError(f"endpoint {self.endpoint} 不可达: {exc}") from exc
        body.setdefault("session_id", sid)
        return body

    async def chat_async(self, message: str, *, session_id: str | None = None) -> dict[str, Any]:
        """异步形态：平台引擎内部以 asyncio 调用，这里用同步实现避免引入依赖。"""
        started = time.perf_counter()
        result = self.chat(message, session_id=session_id)
        result.setdefault("latency_ms", int((time.perf_counter() - started) * 1000))
        return result

    def close(self) -> None:
        """释放本地会话；SDK 接入无长连接，这里只做语义收口。"""


def register(client: DemoAgentSDK, *, agent_id: str = "demo-agent") -> SDKHandle:
    """把 SDK 客户端注册给平台（真实项目由 xian_api 的 client registry 持有）。"""
    return SDKHandle(agent_id=agent_id, client=client)
