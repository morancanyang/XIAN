"""LLM 网关：四角色路由 + 成本账 + 熔断降级（技术方案 7.2 / 3.4）。

真实模型通过 ``xian_core.llm.transport`` 的 OpenAI 兼容客户端接入；未配置
``XIAN_LLM_BASE_URL`` + ``XIAN_LLM_API_KEY``、或连续失败触发熔断时，自动退化为
本地确定性回放，保证离线环境仍能跑通全链路（演示 / CI）。
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from ..config import settings
from .transport import ChatResult, OpenAICompatTransport, ProbeResult, normalize_base_url

Role = Literal["redteam", "target", "judge", "embedding"]

#: 熔断：连续失败达到该次数后，一段时间内直接走离线回放，避免每次调用都白等超时
CIRCUIT_FAIL_THRESHOLD = 3
CIRCUIT_COOLDOWN_S = 300.0


@dataclass
class LLMResponse:
    text: str
    model: str
    role: Role
    prompt_tokens: int = 0
    completion_tokens: int = 0
    degraded: bool = False

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def json(self) -> dict[str, Any]:
        """尽力从输出中解析 JSON（裁判结构化输出用）。"""
        text = self.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except (json.JSONDecodeError, ValueError):
                    return {}
        return {}


@dataclass
class CostLedger:
    """LLM 成本账：战役预算熔断的核心依据（技术方案 13 R-06）。"""

    entries: list[dict[str, Any]] = field(default_factory=list)

    def add(self, resp: LLMResponse, cost_per_1k: float = 0.002) -> None:
        self.entries.append(
            {
                "role": resp.role,
                "model": resp.model,
                "tokens": resp.total_tokens,
                "cost": round(resp.total_tokens / 1000 * cost_per_1k, 6),
                "degraded": resp.degraded,
            }
        )

    @property
    def tokens(self) -> int:
        return sum(e["tokens"] for e in self.entries)

    @property
    def cost(self) -> float:
        return round(sum(e["cost"] for e in self.entries), 6)

    def summary(self) -> dict[str, Any]:
        online = [e for e in self.entries if not e["degraded"]]
        return {
            "calls": len(self.entries),
            "online_calls": len(online),
            "tokens": self.tokens,
            "cost": self.cost,
        }


class LLMGateway:
    """统一网关：模型路由 / 限流 / 成本核算 / 熔断降级。"""

    def __init__(self) -> None:
        self._transport: OpenAICompatTransport | None = None
        self._fail_streak = 0
        self._circuit_open_until = 0.0
        self._last_error = ""
        self._last_probe: ProbeResult | None = None
        self._last_probe_at = 0.0
        self.ledger = CostLedger()

    # ------------------------------------------------------------------ 配置
    def _build_transport(self) -> OpenAICompatTransport:
        cfg = settings.llm
        return OpenAICompatTransport(
            base_url=cfg.base_url,
            api_key=cfg.api_key,
            timeout_s=cfg.timeout_s,
            max_retries=cfg.max_retries,
            provider=cfg.provider,
            probe_model=cfg.redteam_model,
        )

    @property
    def transport(self) -> OpenAICompatTransport | None:
        """按当前配置惰性构建传输层；未配置供应商时为 ``None``（离线）。"""
        if self._transport is None:
            candidate = self._build_transport()
            if candidate.configured:
                self._transport = candidate
        return self._transport

    def configure(
        self,
        *,
        base_url: str,
        api_key: str,
        models: dict[str, str] | None = None,
        provider: str = "",
    ) -> None:
        """运行时热更新接入配置（管理端「大模型接入」卡片用）。

        仅写进程内存与当前 ``settings``，不落盘；持久化仍以 ``.env`` 为准。
        """
        # 归一化后回写：管理端与 status 接口看到的就是实际请求的端点
        settings.llm.base_url = normalize_base_url(base_url)
        settings.llm.api_key = api_key
        if provider:
            settings.llm.provider = provider
        for role, model in (models or {}).items():
            attr = f"{role}_model"
            if model.strip() and hasattr(settings.llm, attr):
                setattr(settings.llm, attr, model.strip())
        self._transport = None
        self._fail_streak = 0
        self._circuit_open_until = 0.0
        self._last_error = ""

    async def aclose(self) -> None:
        if self._transport is not None:
            await self._transport.aclose()
            self._transport = None

    # ------------------------------------------------------------------ 熔断
    def _circuit_open(self) -> bool:
        return time.monotonic() < self._circuit_open_until

    def _record_failure(self, message: str) -> None:
        self._fail_streak += 1
        self._last_error = message[-300:]
        if self._fail_streak >= CIRCUIT_FAIL_THRESHOLD:
            self._circuit_open_until = time.monotonic() + CIRCUIT_COOLDOWN_S
            self._fail_streak = 0

    @property
    def offline(self) -> bool:
        """当前是否处于离线态：未配置供应商，或熔断窗口内。

        离线时调用方应改用本地确定性判定，而不是反复打一个必然失败的端点。
        """
        transport = self.transport
        if transport is None:
            return True
        return self._circuit_open()

    def model_for(self, role: Role) -> str:
        return {
            "redteam": settings.llm.redteam_model,
            "target": settings.llm.target_model,
            "judge": settings.llm.judge_model,
            "embedding": settings.llm.embedding_model,
        }[role]

    # ------------------------------------------------------------------ 补全
    async def complete(
        self,
        prompt: str,
        *,
        role: Role = "redteam",
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        model: str | None = None,
    ) -> LLMResponse:
        target = model or self.model_for(role)
        transport = self.transport
        if transport is not None and not self._circuit_open():
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            try:
                result: ChatResult = await transport.chat(
                    messages,
                    model=target,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=role == "judge",
                )
                self._fail_streak = 0
                out = LLMResponse(
                    text=result.text,
                    model=result.model,
                    role=role,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                )
                self.ledger.add(out)
                return out
            except Exception as exc:  # noqa: BLE001 - 网关对所有供应商错误统一兜底降级
                self._record_failure(str(exc))
                if not settings.llm.fallback_model:
                    return self._offline_complete(prompt, role=role, system=system, target=target)
                try:
                    fallback = await transport.chat(
                        messages,
                        model=settings.llm.fallback_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    out = LLMResponse(
                        text=fallback.text,
                        model=fallback.model,
                        role=role,
                        prompt_tokens=fallback.prompt_tokens,
                        completion_tokens=fallback.completion_tokens,
                        degraded=True,
                    )
                    self.ledger.add(out)
                    return out
                except Exception:  # noqa: BLE001 - 兜底模型也失败则离线回放
                    return self._offline_complete(prompt, role=role, system=system, target=target)
        return self._offline_complete(prompt, role=role, system=system, target=target)

    async def embed(self, text: str) -> list[float]:
        transport = self.transport
        if transport is not None and self.model_for("embedding") and not self._circuit_open():
            try:
                vectors = await transport.embed(text, model=self.model_for("embedding"))
                self._fail_streak = 0
                return vectors
            except Exception as exc:  # noqa: BLE001 - 向量失败时退回确定性哈希
                self._record_failure(str(exc))
        return _deterministic_embedding(text)

    # ------------------------------------------------------------------ 探测
    async def probe(self, *, force: bool = False, ttl_s: float = 30.0) -> ProbeResult:
        """探测真实端点连通性，结果按 TTL 缓存，避免前端轮询把供应商打爆。"""
        now = time.monotonic()
        if not force and self._last_probe is not None and now - self._last_probe_at < ttl_s:
            return self._last_probe
        transport = self.transport
        if transport is None:
            result = ProbeResult(False, 0, "未配置 XIAN_LLM_BASE_URL / XIAN_LLM_API_KEY")
        else:
            result = await transport.probe()
        self._last_probe = result
        self._last_probe_at = now
        if result.ok:
            self._fail_streak = 0
            self._circuit_open_until = 0.0
        return result

    def status(self) -> dict[str, Any]:
        """网关快照：给 /healthz、管理端「大模型接入」卡片和 CLI 用。"""
        cfg = settings.llm
        return {
            "provider": cfg.provider or "custom",
            "base_url": cfg.base_url,
            "models": {role: self.model_for(role) for role in ("redteam", "target", "judge", "embedding")},
            "configured": bool(self.transport is not None),
            "offline": self.offline,
            "circuit_open": self._circuit_open(),
            "last_error": self._last_error,
            "timeout_s": cfg.timeout_s,
            "max_retries": cfg.max_retries,
            **self.ledger.summary(),
        }

    # ------------------------------------------------------------------ 离线回放
    def _offline_complete(self, prompt: str, *, role: Role, system: str, target: str) -> LLMResponse:
        """确定性离线回放：不依赖外部模型，保证演示 / CI 可复现。"""
        if role == "judge":
            body = json.dumps(
                {
                    "verdict": "fail",
                    "confidence": 0.55,
                    "rule_hits": [],
                    "evidence": [],
                    "reason": "离线回放：LLM judge 不可用且未检出黄金信号，判定失败（已由本地裁判降级接管）",
                },
                ensure_ascii=False,
            )
        elif role == "embedding":
            body = ""
        else:
            body = prompt[:512]
        out = LLMResponse(text=body, model=f"offline::{target}", role=role, degraded=True)
        self.ledger.add(out, cost_per_1k=0.0)
        return out


def _deterministic_embedding(text: str, dim: int = 64) -> list[float]:
    """无外部 embedding 服务时的确定性哈希向量（仅用于本地检索回归）。"""
    vec = [0.0] * dim
    if not text:
        return vec
    for token in re.findall(r"[\w\u4e00-\u9fff]+", text.lower()):
        h = hash(token) % dim
        vec[h] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [round(v / norm, 6) for v in vec]


gateway = LLMGateway()