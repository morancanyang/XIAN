"""Mock 沙箱运行时（技术方案 11.4 降级策略）。

无 Docker 的开发/教学环境下，用内存 + 本地 SQLite/JSON 模拟"假订单库 / 假邮件 /
假内部 Wiki"，使除真实容器隔离以外的全部链路（实例化 → 蜜标植入 → 攻击 → 判定 →
报告）可在一个进程内闭环运行。
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..schemas.scenario import ScenarioDsl
from .network import EgressProxy


@dataclass(slots=True)
class MockInstance:
    instance_id: str
    scenario_code: str
    compose_project: str
    status: str = "running"
    seed: dict[str, Any] = field(default_factory=dict)
    canaries: list[dict[str, Any]] = field(default_factory=list)
    destroyed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "scenario_code": self.scenario_code,
            "compose_project": self.compose_project,
            "status": self.status,
            "canaries": len(self.canaries),
            "destroyed": self.destroyed,
            "runtime": "mock",
        }


class MockRuntime:
    """内存态沙箱：与 :class:`DockerRuntime` 同一接口，供上层无感切换。"""

    def __init__(self, workspace: Path | None = None) -> None:
        self.workspace = workspace or Path("outputs/sandbox")
        self.instances: dict[str, MockInstance] = {}
        self.proxies: dict[str, EgressProxy] = {}

    # ---------------------------------------------------------------- 生命周期
    def provision(self, dsl: ScenarioDsl, *, seed: dict[str, Any], canaries: list[dict[str, Any]]) -> MockInstance:
        instance_id = str(uuid.uuid4())
        project = f"mock-{dsl.id}-{instance_id[:8]}"
        instance = MockInstance(
            instance_id=instance_id,
            scenario_code=dsl.id,
            compose_project=project,
            seed=seed,
            canaries=canaries,
        )
        self.instances[instance_id] = instance
        self.proxies[instance_id] = EgressProxy(
            canary_values=tuple(c["value"] for c in canaries if c.get("status") == "planted")
        )
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / f"{project}.json").write_text(
            json.dumps(instance.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return instance

    def status(self, instance_id: str) -> str:
        return self.instances[instance_id].status

    def proxy(self, instance_id: str) -> EgressProxy:
        if instance_id not in self.proxies:
            raise KeyError(f"实例 {instance_id} 不存在")
        return self.proxies[instance_id]

    def execute_tool(self, instance_id: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """模拟工具执行：蜜标值写入"数据库"、触发工具审计，不产生任何真实副作用。"""
        instance = self.instances[instance_id]
        tool = next((t for t in dsl_like_tools(instance) if t["name"] == name), None)
        if tool is None:
            return {"ok": False, "error": f"场景 {instance.scenario_code} 未声明工具 {name}"}
        if tool.get("require_confirm") and not arguments.pop("_confirmed", False):
            return {"ok": False, "error": f"工具 {name} 需要二次确认", "blocked_by": "confirm_required"}
        if tool.get("scope") in {"write", "exec", "network"}:
            decision = self.proxy(instance_id).intercept(
                domain=f"{name}.xian-internal.example", body=json.dumps(arguments, ensure_ascii=False)
            )
            if decision.canary_hit:
                return {"ok": True, "canary_hit": True, "via": "egress", "tool": name}
        return {"ok": True, "tool": name, "result": f"[mock] {name} 已执行", "canary_hit": False}

    def snapshot(self, instance_id: str) -> dict[str, Any]:
        instance = self.instances[instance_id]
        payload = instance.to_dict()
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return {"snapshot_id": digest[:32], "instance": payload}

    def destroy(self, instance_id: str) -> dict[str, Any]:
        instance = self.instances.get(instance_id)
        if instance is None:
            return {"instance_id": instance_id, "status": "not_found"}
        instance.status = "destroyed"
        instance.destroyed = True
        snap = self.snapshot(instance_id)
        self.proxies.pop(instance_id, None)
        return {"instance_id": instance_id, "status": "destroyed", "snapshot": snap, "canary_ledger_kept": True}

    def active(self) -> list[MockInstance]:
        return [i for i in self.instances.values() if not i.destroyed]


def dsl_like_tools(instance: MockInstance) -> list[dict[str, Any]]:
    from ..scenarios import require_template

    template = require_template(instance.scenario_code)
    return [
        {
            "name": t.name,
            "scope": str(t.scope),
            "risk_level": t.risk_level,
            "require_confirm": t.require_confirm,
        }
        for t in template.dsl.tools
    ]