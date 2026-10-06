"""大模型接入：网关状态 / 连通性探测 / 运行时热更新（技术方案 7.2）。

设计约束：
- Key 只进进程内存，不落盘、不进日志；持久化一律走 ``.env`` 的 ``XIAN_LLM_*``。
- 探测接口带 TTL 缓存，前端轮询不会把供应商额度打掉。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from xian_core.config import PROVIDER_PRESETS, resolve_provider
from xian_core.llm.gateway import gateway

from ..deps import PrincipalDep

router = APIRouter(prefix="/llm", tags=["llm"])


class LLMConfigIn(BaseModel):
    """运行时接入配置；留空的字段保持原值。"""

    base_url: str = Field(default="", description="OpenAI 兼容端点，例如 https://api.deepseek.com")
    api_key: str = Field(default="", description="API Key；空字符串表示不修改")
    provider: str = Field(default="", description="供应商标识，留空按端点自动识别")
    redteam_model: str = ""
    target_model: str = ""
    judge_model: str = ""
    embedding_model: str = ""


def _mask_key(key: str) -> str:
    """Key 只回显前缀与长度，避免明文经 API 外泄。"""
    key = key or ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}…{key[-4:]} ({len(key)})"


def _current_key() -> str:
    """读取当前生效的 Key（仅用于打码回显，不做任何持久化）。"""
    from xian_core.config import get_settings

    return get_settings().llm.api_key


@router.get("/status")
async def llm_status(_principal: PrincipalDep) -> dict[str, Any]:
    """网关快照：是否在线、四角色模型路由、熔断状态、成本账。"""
    payload = dict(gateway.status())
    payload["api_key"] = _mask_key(_current_key())
    return payload


@router.get("/providers")
async def llm_providers(_principal: PrincipalDep) -> dict[str, Any]:
    """可选供应商预设，供管理端下拉选择。"""
    return {
        "providers": [
            {"name": name, "base_url": meta["base_url"], "models": {
                "redteam": meta.get("redteam_model", ""),
                "target": meta.get("target_model", ""),
                "judge": meta.get("judge_model", ""),
                "embedding": meta.get("embedding_model", ""),
            }}
            for name, meta in PROVIDER_PRESETS.items()
        ]
    }


@router.post("/probe")
async def llm_probe(_principal: PrincipalDep, force: bool = True) -> dict[str, Any]:
    """实时探测端点连通性：默认强制刷新，返回延迟与可用模型列表。"""
    result = await gateway.probe(force=force)
    return {
        "ok": result.ok,
        "latency_ms": result.latency_ms,
        "detail": result.detail,
        "models": list(result.models),
    }


@router.post("/config")
async def llm_config(body: LLMConfigIn, _principal: PrincipalDep) -> dict[str, Any]:
    """热更新接入配置（内存态，重启后回到 ``.env``）。保存后立即探测一次。"""
    from xian_core.config import get_settings

    cfg = get_settings().llm
    base_url = body.base_url.strip() or cfg.base_url
    api_key = body.api_key.strip() or cfg.api_key
    provider = resolve_provider(body.provider, base_url, api_key)
    if body.provider.lower() in PROVIDER_PRESETS:
        provider = body.provider.lower()
        if not body.base_url.strip():
            base_url = PROVIDER_PRESETS[provider]["base_url"]
    gateway.configure(
        base_url=base_url,
        api_key=api_key,
        provider=provider,
        models={
            "redteam": body.redteam_model,
            "target": body.target_model,
            "judge": body.judge_model,
            "embedding": body.embedding_model,
        },
    )
    result = await gateway.probe(force=True)
    payload = dict(gateway.status())
    payload["api_key"] = _mask_key(get_settings().llm.api_key)
    payload["probe"] = {"ok": result.ok, "latency_ms": result.latency_ms, "detail": result.detail}
    return payload