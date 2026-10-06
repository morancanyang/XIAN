"""XIAN 红蓝对抗平台核心库。

本包承载技术方案（技术与实施方案.md）中"核心库层"的全部领域实现，对外以
`xian_core` 顶层包暴露稳定符号，供 `services/api`、`services/worker`、`services/cli`
三个服务进程复用，保证业务规则只有一份实现。

分层结构（技术方案 2.1 四层架构）：::

    xian_core.config / errors / contracts / schemas   —— 全局配置、领域异常、跨进程契约
    xian_core.db                                       —— 数据访问层（模型 + 仓储 + 会话）
    xian_core.identity / agents / scenarios / sandbox   —— 业务域
    xian_core.redteam / judge / scoring / sessions      —— 攻防引擎域
    xian_core.levels / ops / remediation / reports      —— 演练、运营与治理域
    xian_core.llm / storage / bus / notify              —— 基础设施适配层
"""

from . import (
    agents,
    bus,
    cases,
    config,
    contracts,
    db,
    errors,
    identity,
    judge,
    levels,
    llm,
    matrix,
    notify,
    ops,
    redteam,
    remediation,
    reports,
    sandbox,
    scenarios,
    scoring,
    sessions,
    storage,
)

__all__ = [
    "agents",
    "bus",
    "cases",
    "config",
    "contracts",
    "db",
    "errors",
    "identity",
    "judge",
    "levels",
    "llm",
    "matrix",
    "notify",
    "ops",
    "redteam",
    "remediation",
    "reports",
    "sandbox",
    "scenarios",
    "scoring",
    "sessions",
    "storage",
]

__version__ = "1.0.0"