"""OpenAI 兼容 LLM 传输层：httpx 直连 ``/chat/completions`` 与 ``/embeddings``。

设计取舍：不引入 litellm 这类重依赖。任何 OpenAI 兼容端点——DeepSeek、Moonshot、
DashScope compatible-mode、SiliconFlow、智谱、vLLM、Ollama、LiteLLM Proxy——都能用
同一份代码接入，缺的只是 ``XIAN_LLM_BASE_URL`` + ``XIAN_LLM_API_KEY``（技术方案 7.2）。

回环地址（本地 vLLM / Ollama / LiteLLM Proxy）禁用环境变量代理，否则会被本机代理劫持。
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

from ..errors import LLMProviderError

#: 这些状态码值得重试：限流与供应商侧瞬时故障。
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


@dataclass(frozen=True, slots=True)
class ChatResult:
    """一次对话补全的结构化结果（已剥离供应商私有字段）。"""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """连通性探测结果：``GET {base}/models`` 成功或一次最小补全成功。"""

    ok: bool
    latency_ms: int
    detail: str
    models: tuple[str, ...] = ()


def normalize_base_url(base_url: str) -> str:
    """把用户填写的端点归一化成 OpenAI 兼容根路径（以 ``/v1`` 结尾）。

    ``https://api.deepseek.com`` / ``https://api.deepseek.com/v1`` /
    ``https://api.deepseek.com/v1/`` 三种写法都会得到同一个结果。
    """
    raw = (base_url or "").strip().rstrip("/")
    if not raw:
        return ""
    if "://" not in raw:
        raw = f"http://{raw}"
    # 末尾已是版本段（/v1、/v4 ...）就不再追加，兼容智谱 /api/paas/v4 这类不带 /v1 的端点
    if re.fullmatch(r"v\d+", raw.rsplit("/", 1)[-1]):
        return raw
    return f"{raw}/v1"


def is_loopback(base_url: str) -> bool:
    """回环地址必须绕过环境变量代理，否则请求会被本机代理拒绝。"""
    host = (urlparse(base_url if "://" in base_url else f"http://{base_url}").hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1", "0.0.0.0"} or host.startswith("127.")


@dataclass(slots=True)
class OpenAICompatTransport:
    """OpenAI 兼容端点的最小可用客户端：对话、向量、连通性探测。"""

    base_url: str
    api_key: str
    timeout_s: float = 60.0
    max_retries: int = 2
    extra_headers: dict[str, str] = field(default_factory=dict)
    provider: str = "custom"
    probe_model: str = ""
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.base_url = normalize_base_url(self.base_url)

    # ------------------------------------------------------------------ 生命周期
    @property
    def configured(self) -> bool:
        """配齐 base_url 与 api_key 才算可用；缺任何一个都视为离线。"""
        return bool(self.base_url) and bool(self.api_key.strip())

    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout_s),
                trust_env=is_loopback(self.base_url),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    **self.extra_headers,
                },
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    # ------------------------------------------------------------------ 请求核心
    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """带有限次重试的 POST；重试耗尽后抛出可读的 ``LLMProviderError``。"""
        attempts = max(1, self.max_retries + 1)
        last: str = ""
        for attempt in range(attempts):
            try:
                resp = await self._http().post(path, json=payload)
                if resp.status_code < 400:
                    return resp.json()
                last = f"HTTP {resp.status_code}: {resp.text[:200]}"
                if resp.status_code not in RETRYABLE_STATUS:
                    # 401/403/404 这类重试没有意义，直接失败
                    break
            except httpx.TimeoutException as exc:
                last = f"超时（{self.timeout_s:g}s）: {exc}"
            except httpx.HTTPError as exc:
                last = f"网络错误: {exc}"
            if attempt + 1 < attempts:
                await asyncio.sleep(min(2.0, 0.4 * (2**attempt)))
        raise LLMProviderError(f"LLM 端点 {self.base_url}{path} 调用失败：{last or '未知错误'}")

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> ChatResult:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_mode:
            # 裁判结构化输出：能开 JSON 模式的端点才加，避免端点不识别直接 400
            payload["response_format"] = {"type": "json_object"}
        body = await self._post("/chat/completions", payload)
        choices = body.get("choices") or []
        if not choices:
            raise LLMProviderError(f"LLM 端点返回空 choices：{str(body)[:200]}")
        message = choices[0].get("message") or {}
        usage = body.get("usage") or {}
        return ChatResult(
            text=str(message.get("content") or ""),
            model=str(body.get("model") or model),
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )

    async def embed(self, text: str, *, model: str) -> list[float]:
        body = await self._post("/embeddings", {"model": model, "input": text})
        data = body.get("data") or []
        if not data:
            raise LLMProviderError(f"embedding 端点返回空 data：{str(body)[:200]}")
        return [float(v) for v in (data[0].get("embedding") or [])]

    async def probe(self) -> ProbeResult:
        """连通性探测：优先 ``GET /models``（免费），失败再试一次最小补全。"""
        started = time.perf_counter()
        try:
            resp = await self._http().get("/models")
        except httpx.HTTPError as exc:
            return ProbeResult(False, _elapsed_ms(started), f"网络不可达：{exc}")
        if resp.status_code < 400:
            try:
                ids = [str(m.get("id", "")) for m in resp.json().get("data", []) if m.get("id")]
            except ValueError:
                ids = []
            return ProbeResult(True, _elapsed_ms(started), "端点可用", tuple(ids[:20]))
        # 少数端点不开放 /models，退化为 1 token 的最小补全
        try:
            await self._post("/chat/completions", {
                "model": self.probe_model or "xian-probe",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            })
        except LLMProviderError as exc:
            return ProbeResult(False, _elapsed_ms(started), str(exc)[:200])
        return ProbeResult(True, _elapsed_ms(started), "最小补全可达")


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)