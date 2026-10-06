"""快照与销毁（技术方案 9.3：沙箱销毁与快照）。

销毁 = 停止并删除容器/网络/卷 + 归档种子数据快照 + 保留蜜标台账；
快照用于复测时复用同一份假数据，保证前后可比（PRD 3.7.5.2 前置条件）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ARCHIVE_DIR = Path("outputs/snapshots")


@dataclass(slots=True)
class Snapshot:
    snapshot_id: str
    scenario_code: str
    instance_id: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "scenario_code": self.scenario_code,
            "instance_id": self.instance_id,
            "payload": self.payload,
        }


def fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def make_snapshot(*, scenario_code: str, instance_id: str, payload: dict[str, Any]) -> Snapshot:
    return Snapshot(
        snapshot_id=fingerprint({"scenario": scenario_code, "instance": instance_id, "payload": payload}),
        scenario_code=scenario_code,
        instance_id=instance_id,
        payload=payload,
    )


def persist(snapshot: Snapshot, directory: Path | None = None) -> Path:
    target_dir = directory or ARCHIVE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{snapshot.scenario_code}-{snapshot.snapshot_id}.json"
    path.write_text(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load(snapshot_id: str, directory: Path | None = None) -> Snapshot | None:
    target_dir = directory or ARCHIVE_DIR
    for path in target_dir.glob(f"*-{snapshot_id}.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        return Snapshot(
            snapshot_id=data["snapshot_id"],
            scenario_code=data["scenario_code"],
            instance_id=data["instance_id"],
            payload=data.get("payload", {}),
        )
    return None


def teardown_report(*, scenario_code: str, instance_id: str, kept_canaries: int, snapshot_id: str) -> dict[str, Any]:
    """销毁结果：环境删除、种子数据归档、蜜标台账保留。"""
    return {
        "scenario_code": scenario_code,
        "instance_id": instance_id,
        "environment": "removed",
        "snapshot_id": snapshot_id,
        "canary_ledger_kept": True,
        "kept_canaries": kept_canaries,
    }