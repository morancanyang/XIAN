"""通用领域模型：分页、枚举、ID 类型（OpenAPI 契约的事实源）。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum, StrEnum
from typing import Annotated, Any, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


def new_uuid() -> UUID:
    return uuid4()


def enum_str(value: Any) -> str:
    """把枚举/字符串统一归一为字符串值（兼容 Python 3.11+ 的 str(Enum) 行为变化）。"""
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


class StrictModel(BaseModel):
    """所有对外契约模型的基类：禁止未知字段，序列化按别名。"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, use_enum_values=True)


class Timestamped(StrictModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    updated_at: datetime | None = None


class Page[T](BaseModel):
    """普通列表规则：默认 20 条，可调 10/50/100（PRD 2.3.2）。"""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int = 1
    size: int = 20

    @property
    def pages(self) -> int:
        return max(1, (self.total + self.size - 1) // self.size)


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    keyword: str | None = None
    sort_by: str | None = None
    sort_desc: bool = False


class AccessType(StrEnum):
    http = "http"
    sdk = "sdk"
    container = "container"


class AgentStatus(StrEnum):
    """Agent 资产状态机（技术方案 2.2）：未验证 → 已归属验证 → 演练中 → 已归档 / 下线。"""

    unverified = "unverified"
    active = "active"
    testing = "testing"
    offline = "offline"
    archived = "archived"


class OwnershipMethod(StrEnum):
    dns_txt = "dns_txt"
    image_digest = "image_digest"


class OwnershipResult(StrEnum):
    verified = "verified"
    pending = "pending"
    failed = "failed"


class Intensity(StrEnum):
    recon = "recon"
    standard = "standard"
    deep = "deep"


class JudgeMode(StrEnum):
    loose = "loose"
    standard = "standard"
    strict = "strict"


class OutputMode(StrEnum):
    summary = "summary"
    full = "full"
    reproducible = "reproducible"


class CampaignStatus(StrEnum):
    """PRD 2.2.4 战役状态机。"""

    draft = "draft"
    scheduled = "scheduled"
    preparing = "preparing"
    attacking = "attacking"
    analyzing = "analyzing"
    reporting = "reporting"
    completed = "completed"
    cancelled = "cancelled"
    tripped = "tripped"
    env_failed = "env_failed"
    failed = "failed"  # 战役执行抛出未预期异常时的终态（campaigns.run 写入）


class Verdict(StrEnum):
    success = "success"
    partial = "partial"
    fail = "fail"
    unavailable = "unavailable"


class JudgeLevel(StrEnum):
    golden = "golden"
    classifier = "classifier"
    llm = "llm"


class SessionMode(StrEnum):
    console = "console"
    level = "level"
    defense = "defense"


class SessionStatus(StrEnum):
    active = "active"
    paused = "paused"
    completed = "completed"
    aborted = "aborted"
    archived = "archived"


class Role(StrEnum):
    owner = "owner"
    blue = "blue"
    red = "red"
    analyst = "analyst"
    admin = "admin"


class Severity(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Difficulty(StrEnum):
    beginner = "beginner"
    easy = "easy"
    low = "low"
    medium = "medium"
    hard = "hard"
    expert = "expert"


class ToolScope(StrEnum):
    read = "read"
    write = "write"
    exec = "exec"
    network = "network"


AnnotatedUUID = Annotated[UUID, Field(default_factory=new_uuid)]