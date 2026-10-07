"""沙箱运行时、网络隔离、蜜标检测、快照与实例池（PRD 3.1 / 技术方案 9.3）。"""

from .canary import CanaryHit, scan_egress, scan_text, scan_tool_call, summarize
from .mock_runtime import MockInstance, MockRuntime
from .network import (
    DEFAULT_ALLOWLIST,
    EgressDecision,
    EgressProxy,
    assert_no_real_credential,
    validate_allowlist,
)
from .pool import PooledInstance, SandboxPool, require_pool_slot
from .runtime import DockerRuntime, compose_file_for, docker_available
from .registry import (
    active_instances,
    client_for,
    destroy_instance,
    get_runtime,
    instance_for,
    provision_instance,
)
from .registry import reset as reset_registry
from .snapshot import Snapshot, fingerprint, load, make_snapshot, persist, teardown_report

__all__ = [
    "DEFAULT_ALLOWLIST",
    "CanaryHit",
    "DockerRuntime",
    "EgressDecision",
    "EgressProxy",
    "MockInstance",
    "MockRuntime",
    "PooledInstance",
    "SandboxPool",
    "Snapshot",
    "active_instances",
    "client_for",
    "destroy_instance",
    "get_runtime",
    "instance_for",
    "provision_instance",
    "reset_registry",
    "assert_no_real_credential",
    "compose_file_for",
    "docker_available",
    "fingerprint",
    "load",
    "make_snapshot",
    "persist",
    "require_pool_slot",
    "scan_egress",
    "scan_text",
    "scan_tool_call",
    "summarize",
    "teardown_report",
    "validate_allowlist",
]