"""领域异常与全局错误约定（对齐 PRD 2.3.1 全局异常处理）。"""

from __future__ import annotations

from typing import Any


class XianError(Exception):
    """领域异常基类。

    ``code`` 为稳定机器码，``hint`` 为面向用户的处理建议文案（PRD 2.3.1）。
    """

    http_status: int = 400
    code: str = "xian.error"
    hint: str = "系统开小差啦，请联系管理员"

    def __init__(self, message: str = "", **context: Any) -> None:
        super().__init__(message or self.code)
        self.message = message or self.code
        self.context = context

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "hint": self.hint, "context": self.context}


class ValidationError(XianError):
    http_status = 422
    code = "xian.validation_error"
    hint = "请求参数不合法，请检查后重试"


class NotFoundError(XianError):
    http_status = 404
    code = "xian.not_found"
    hint = "数据异常或不存在"


class PermissionDenied(XianError):
    http_status = 403
    code = "xian.permission_denied"
    hint = "无操作权限"


class QuotaExceeded(XianError):
    http_status = 429
    code = "xian.quota_exceeded"
    hint = "租户配额已用尽，请升级套餐或联系管理员"


class OwnershipNotVerified(XianError):
    http_status = 403
    code = "xian.ownership_not_verified"
    hint = "该 Agent 未通过归属校验，请先完成 DNS TXT 或镜像摘要校验"


class SandboxEnvFailed(XianError):
    http_status = 503
    code = "xian.sandbox_env_failed"
    hint = "演练环境准备失败，请检查接入配置"


class EgressBlocked(XianError):
    http_status = 403
    code = "xian.egress_blocked"
    hint = "安全代理异常，演练已暂停（防止真实外联）"


class BudgetTripped(XianError):
    http_status = 409
    code = "xian.budget_tripped"
    hint = "已达到本次演练预算上限，已基于现有结果生成报告"


class TargetUnavailable(XianError):
    http_status = 504
    code = "xian.target_unavailable"
    hint = "被测 Agent 无响应，请检查网络连接后重试"


class JudgeDegraded(XianError):
    http_status = 206
    code = "xian.judge_degraded"
    hint = "判定服务降级，部分结论未经过 LLM 复核"


class LLMProviderError(XianError):
    http_status = 503
    code = "xian.llm_provider_error"
    hint = "模型服务繁忙，已排队"


class ExportForbidden(XianError):
    http_status = 403
    code = "xian.export_forbidden"
    hint = "武器库原始载荷默认不可导出（权限管控）"


class CanaryCollision(XianError):
    http_status = 409
    code = "xian.canary_collision"
    hint = "检测到疑似真实凭证混入演练环境，演练已被安全策略阻止"


# 全局异常 -> 提示文案映射（PRD 2.3.1）
GLOBAL_EXCEPTION_HINTS: dict[str, str] = {
    "network": "请检查网络连接",
    "timeout": "系统响应超时，请稍后重试",
    "permission": "无操作权限",
    "system": "系统开小差啦，请联系管理员",
    "data": "数据异常或不存在",
}