"""沙箱实例池：复用就绪实例、回收过期实例（PRD 3.1.4 后置条件）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..errors import SandboxEnvFailed as SandboxError


@dataclass(slots=True)
class PooledInstance:
    instance_id: str
    scenario_code: str
    status: str = "ready"
    reuse_count: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


class SandboxPool:
    """按场景代码聚合并发复用实例；默认不复用已销毁实例。"""

    def __init__(self, *, max_idle_per_scenario: int = 2) -> None:
        self.max_idle = max_idle_per_scenario
        self._by_scenario: dict[str, list[PooledInstance]] = {}

    def acquire(self, scenario_code: str) -> PooledInstance | None:
        ready = [i for i in self._by_scenario.get(scenario_code, []) if i.status == "ready"]
        if not ready:
            return None
        instance = ready[0]
        instance.status = "busy"
        instance.reuse_count += 1
        return instance

    def release(self, instance: PooledInstance) -> None:
        bucket = self._by_scenario.setdefault(instance.scenario_code, [])
        if instance.reuse_count >= self.max_idle:
            instance.status = "recycle"
            return
        instance.status = "ready"
        if instance not in bucket:
            bucket.append(instance)

    def register(self, instance: PooledInstance) -> None:
        bucket = self._by_scenario.setdefault(instance.scenario_code, [])
        if not any(i.instance_id == instance.instance_id for i in bucket):
            bucket.append(instance)

    def recycle(self, scenario_code: str | None = None) -> list[str]:
        removed: list[str] = []
        for code, bucket in self._by_scenario.items():
            if scenario_code and code != scenario_code:
                continue
            for instance in bucket:
                if instance.status == "recycle":
                    removed.append(instance.instance_id)
            self._by_scenario[code] = [i for i in bucket if i.status != "recycle"]
        return removed

    def stats(self) -> dict[str, int]:
        return {code: len([i for i in bucket if i.status == "ready"]) for code, bucket in self._by_scenario.items()}


def require_pool_slot(pool: SandboxPool, scenario_code: str) -> PooledInstance:
    instance = pool.acquire(scenario_code)
    if instance is None:
        raise SandboxError(f"场景 {scenario_code} 无可用实例，请稍后重试或新建实例")
    return instance