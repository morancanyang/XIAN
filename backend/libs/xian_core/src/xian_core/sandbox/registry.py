# -*- coding: utf-8 -*-
"""沙箱实例注册表：进程级持有已实例化的场景运行时。

背景：场景市场点「创建实例」时，HTTP 层只往库里写了一行 ``ScenarioInstance`` 与蜜标
台账，从来没有真正 provision 过运行时。于是 ``SandboxChatClient`` 永远拿不到活实例，
``Campaign.scenario_instance_id`` / ``Session.scenario_instance_id`` 落了库也没人读
—— 「创建完实例然后呢」的答案只能是没有然后。这里把缺口补上：

- ``instantiate`` 调 :func:`provision_instance` 把实例拉起来并登记；
- 两条执行路径（模式一战役 runner、模式二会话 executor）按 instance_id 取客户端；
- ``destroy`` 调 :func:`destroy_instance` 回收，蜜标台账按 PRD 保留在库里。

当前只接 MockRuntime：无 Docker 的开发/教学环境即可全链路闭环；DockerRuntime 的
接口（up/down/ps/logs）与 ChatClient 需要的 execute_tool 并不一致，接入需另行适配。
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Iterable
from typing import Any

from .mock_runtime import MockInstance, MockRuntime

_lock = threading.RLock()
_runtime: MockRuntime | None = None
# 库里 scenario_instances.id -> MockInstance.instance_id（两者当前取同值，保留映射是为了
# 将来换成 DockerRuntime 时不必改动调用方）
_index: dict[str, str] = {}


def get_runtime() -> MockRuntime:
    """进程级单例运行时：所有实例共享一个 MockRuntime 实例。"""
    global _runtime
    with _lock:
        if _runtime is None:
            _runtime = MockRuntime()
        return _runtime


def provision_instance(
    instance_id: Any,
    dsl: Any,
    *,
    seed: dict[str, Any] | None = None,
    canaries: Iterable[dict[str, Any]] = (),
) -> MockInstance:
    """把场景实例拉起来并登记，返回 MockInstance。"""
    key = str(instance_id)
    runtime = get_runtime()
    with _lock:
        instance = runtime.provision(
            dsl, seed=dict(seed or {}), canaries=list(canaries), instance_id=key
        )
        _index[key] = instance.instance_id
        return instance


def instance_for(instance_id: Any) -> MockInstance | None:
    """按库里实例 ID 取运行时实例；未登记返回 None（调用方应回退到 Agent 直连）。"""
    key = str(instance_id)
    with _lock:
        inner = _index.get(key)
    if inner is None:
        return None
    try:
        return get_runtime().instances[inner]
    except KeyError:  # pragma: no cover - 已销毁但索引没清干净
        with _lock:
            _index.pop(key, None)
        return None


def client_for(instance_id: Any) -> Any | None:
    """按库里实例 ID 取 ChatClient；未登记返回 None。"""
    instance = instance_for(instance_id)
    if instance is None:
        return None
    from ..redteam.clients import SandboxChatClient

    return SandboxChatClient(get_runtime(), instance.instance_id)


def destroy_instance(instance_id: Any) -> dict[str, Any] | None:
    """销毁实例并注销；未登记返回 None。"""
    key = str(instance_id)
    with _lock:
        inner = _index.pop(key, None)
    if inner is None:
        return None
    return get_runtime().destroy(inner)


def resume_from_db(rows: Iterable[Any]) -> int:
    """按库里的实例记录重建运行时，返回成功恢复的条数。

    注册表是进程级内存态：API 一重启，上次 provision 的实例就全丢了，
    而库里这些实例还挂着 ``status='ready'``。此时再打战役/会话就会退化成
    "Agent 直连"甚至连接失败——现象就是"明明建过实例却打不通"。
    这里用库里的 seed 快照与蜜标台账把运行时重新拉起来，蜜标值与首次一致。
    """
    from ..scenarios import load_templates

    code_of = {_scenario_uuid(t.code): t for t in load_templates()}
    resumed = 0
    for row in rows:
        template = code_of.get(str(getattr(row, "scenario_id", "")))
        if template is None:
            continue
        canaries = [
            {"type": c.type, "value": c.value, "plant_location": list(c.plant_location), "status": c.status}
            for c in (getattr(row, "canaries", None) or [])
        ]
        provision_instance(
            row.id,
            template.dsl,
            seed=dict(getattr(row, "seed_data_snapshot", None) or {}),
            canaries=canaries,
        )
        resumed += 1
    return resumed


def _scenario_uuid(code: str) -> str:
    """与 scenarios 路由一致的场景编码 -> UUID 派生规则。"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"scenario:{code}"))


def active_instances() -> list[MockInstance]:
    return get_runtime().active()


def reset() -> None:
    """清空注册表（仅供测试使用）。"""
    global _runtime
    with _lock:
        _runtime = None
        _index.clear()
