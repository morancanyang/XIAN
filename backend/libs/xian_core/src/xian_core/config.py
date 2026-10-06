"""全局配置：pydantic-settings 分组加载，启动时 fail-fast 校验（技术方案 7.1）。

分组：db / bus / llm / sandbox / judge / report / security / notify。
开发态从根 ``.env`` 读取；生产态由环境变量 / Vault / K8s Secret 注入。
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DbSettings(BaseSettings):
    """PostgreSQL 主库连接。"""

    model_config = SettingsConfigDict(env_prefix="XIAN_DB_", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    user: str = "xian"
    password: str = "xian"
    name: str = "xian"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False
    dsn_override: str = ""

    @property
    def dsn(self) -> str:
        """优先使用显式 DSN，便于本地零依赖回退 SQLite（XIAN_DB_DSN_OVERRIDE）。"""
        if self.dsn_override:
            return self.dsn_override
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_dsn(self) -> str:
        if self.dsn_override:
            return self.dsn_override.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg")
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class BusSettings(BaseSettings):
    """Redis：Celery broker、WS 事件总线、限流、缓存。"""

    model_config = SettingsConfigDict(env_prefix="XIAN_REDIS_", extra="ignore")

    url: str = "redis://localhost:6379/0"
    channel_prefix: str = "xian"
    event_batch_ms: int = 100  # 控制台事件批量合并窗口（技术方案 11.1）

    @property
    def celery_broker(self) -> str:
        return self.url

    @property
    def celery_backend(self) -> str:
        return self.url


#: 供应商预设：OpenAI 兼容端点 + 默认模型名（技术方案 7.2）。
#: 只填 Key 不填端点时按这里推断；换自建网关时显式写 XIAN_LLM_BASE_URL 即可覆盖。
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "redteam_model": "deepseek-chat",
        "target_model": "deepseek-chat",
        "judge_model": "deepseek-chat",
        "embedding_model": "",
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn",
        "redteam_model": "moonshot-v1-8k",
        "target_model": "moonshot-v1-8k",
        "judge_model": "moonshot-v1-8k",
        "embedding_model": "",
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode",
        "redteam_model": "qwen-plus",
        "target_model": "qwen-plus",
        "judge_model": "qwen-plus",
        "embedding_model": "text-embedding-v3",
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn",
        "redteam_model": "Qwen/Qwen2.5-7B-Instruct",
        "target_model": "Qwen/Qwen2.5-7B-Instruct",
        "judge_model": "Qwen/Qwen2.5-7B-Instruct",
        "embedding_model": "BAAI/bge-m3",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "redteam_model": "glm-4-plus",
        "target_model": "glm-4-plus",
        "judge_model": "glm-4-plus",
        "embedding_model": "embedding-3",
    },
    "openai": {
        "base_url": "https://api.openai.com",
        "redteam_model": "gpt-4o-mini",
        "target_model": "gpt-4o-mini",
        "judge_model": "gpt-4o-mini",
        "embedding_model": "text-embedding-3-small",
    },
}

#: 供应商 -> Key 环境变量名。只配 Key 时据此反推端点与默认模型。
PROVIDER_KEY_ENVS: dict[str, str] = {
    "deepseek": "DEEPSEEK_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
    "siliconflow": "SILICONFLOW_API_KEY",
    "zhipu": "ZHIPU_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def resolve_provider(provider: str = "", base_url: str = "", api_key: str = "") -> str:
    """推断供应商标识：显式指定 > 按端点域名匹配 > 按已存在的 Key 环境变量反推。"""
    name = (provider or "").strip().lower()
    if name in PROVIDER_PRESETS:
        return name
    raw = (base_url or "").lower()
    if raw:
        for preset, meta in PROVIDER_PRESETS.items():
            if meta["base_url"] in raw:
                return preset
    if not (api_key or "").strip():
        for preset, env_name in PROVIDER_KEY_ENVS.items():
            if os.environ.get(env_name, "").strip():
                return preset
    return name


class LLMSettings(BaseSettings):
    """LLM 网关：OpenAI 兼容端点提供 redteam / target / judge / embedding 四角色路由（技术方案 7.2）。

    base_url 与 api_key 均为空时网关判定为离线，所有调用走确定性回放；
    只填 Key 时按 resolve_provider 推断端点与默认模型名。
    """

    model_config = SettingsConfigDict(env_prefix="XIAN_LLM_", extra="ignore")

    provider: str = ""
    base_url: str = ""
    api_key: str = ""
    redteam_model: str = ""
    target_model: str = ""
    judge_model: str = ""
    judge_model_secondary: str = ""  # 双裁判仲裁：不同模型互为对照
    embedding_model: str = ""
    timeout_s: float = 60.0
    max_retries: int = 2
    fallback_model: str = ""

    @model_validator(mode="after")
    def _fill_from_preset(self) -> "LLMSettings":
        """只填 Key 不填端点时，按供应商预设补全 base_url 与默认模型名。"""
        resolved = resolve_provider(self.provider, self.base_url, self.api_key)
        if resolved and resolved in PROVIDER_PRESETS:
            self.provider = resolved
            preset = PROVIDER_PRESETS[resolved]
            if not self.base_url.strip():
                self.base_url = preset["base_url"]
            # 只配了 DEEPSEEK_API_KEY 等通用变量时，直接复用，省一次重复配置
            if not self.api_key.strip():
                self.api_key = os.environ.get(PROVIDER_KEY_ENVS[resolved], "").strip()
            for role in ("redteam", "target", "judge", "embedding"):
                attr = f"{role}_model"
                if not getattr(self, attr).strip() and preset.get(f"{role}_model"):
                    setattr(self, attr, preset[f"{role}_model"])
        if not self.judge_model_secondary.strip():
            self.judge_model_secondary = self.judge_model
        return self

    @property
    def ready(self) -> bool:
        """配齐 base_url + api_key 才认为可在线调用。"""
        return bool(self.base_url.strip()) and bool(self.api_key.strip())


class SandboxSettings(BaseSettings):
    """沙箱与 egress 代理（技术方案 3.5）。"""

    model_config = SettingsConfigDict(env_prefix="XIAN_SANDBOX_", extra="ignore")

    runtime: Literal["docker", "mock"] = "mock"
    workdir: str = "./outputs/sandbox"
    compose_bin: str = "docker"
    max_concurrent_instances: int = 8
    instance_ttl_minutes: int = 120
    egress_enabled: bool = True
    egress_allowlist: str = "api.internal.test,canary-gw.local"
    egress_proxy_image: str = "xian/egress-proxy:dev"
    sandbox_base_image: str = "xian/sandbox-runtime:dev"

    @property
    def egress_allow(self) -> list[str]:
        return [d.strip() for d in self.egress_allowlist.split(",") if d.strip()]

    @field_validator("egress_allowlist")
    @classmethod
    def _no_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("egress_allowlist 不允许为空：egress 默认拒绝（安全默认）")
        return v


class JudgeSettings(BaseSettings):
    """三级裁判配置（PRD 3.6）。"""

    model_config = SettingsConfigDict(env_prefix="XIAN_JUDGE_", extra="ignore")

    mode: Literal["loose", "standard", "strict"] = "standard"
    sample_audit_rate: float = Field(default=0.10, ge=0, le=1)
    max_llm_retries: int = 1
    confidence_floor: float = 0.6
    rules_path: str = "src/xian_core/judge/rules"

    @field_validator("sample_audit_rate")
    @classmethod
    def _rate(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("sample_audit_rate 必须在 [0,1]")
        return v


class ReportSettings(BaseSettings):
    """报告渲染（Jinja2 + Playwright-Chromium，技术方案 D9）。"""

    model_config = SettingsConfigDict(env_prefix="XIAN_REPORT_", extra="ignore")

    engine: Literal["jinja", "chromium"] = "jinja"
    max_render_seconds: int = 120
    share_default_ttl_hours: int = 72
    watermark: bool = True


class SecuritySettings(BaseSettings):
    """凭证加密与脱敏（技术方案 9.2）。"""

    model_config = SettingsConfigDict(env_prefix="XIAN_SECURITY_", extra="ignore")

    secret_key: str = "dev-insecure-secret-key-change-me"
    retention_days: int = 180
    canary_namespace: str = "sk-canary"

    @field_validator("secret_key")
    @classmethod
    def _key_len(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("secret_key 至少 16 位（用于接入凭证加密存储）")
        return v


class NotifySettings(BaseSettings):
    """通知渠道：站内 / 邮件 / IM Webhook（PRD 3.3.6.8.1）。"""

    model_config = SettingsConfigDict(env_prefix="XIAN_NOTIFY_", extra="ignore")

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "xian@localhost"
    im_webhook_url: str = ""
    max_retries: int = 3


class Settings(BaseSettings):
    """应用总配置：启动时校验，缺项 fail-fast。"""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["dev", "staging", "prod"] = "dev"
    debug: bool = True
    app_name: str = "xian"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    db: DbSettings = Field(default_factory=DbSettings)
    bus: BusSettings = Field(default_factory=BusSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    sandbox: SandboxSettings = Field(default_factory=SandboxSettings)
    judge: JudgeSettings = Field(default_factory=JudgeSettings)
    report: ReportSettings = Field(default_factory=ReportSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    notify: NotifySettings = Field(default_factory=NotifySettings)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """进程内单例配置。测试可通过 ``get_settings.cache_clear()`` 重置。"""
    return Settings()


settings = get_settings()