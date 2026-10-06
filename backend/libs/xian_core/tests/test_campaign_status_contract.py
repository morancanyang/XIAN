"""战役状态枚举契约：后端写入的每个 status 都必须在枚举与前端标签里存在。

背景：campaigns.run 在战役执行抛异常时写入 status="failed"，但 CampaignStatus
枚举里没有这个成员，导致 `CampaignOut.model_validate` 直接 500，
整个 GET /api/v1/campaigns 列表页打不开。这里把契约锁死，避免再漂移。
"""

from __future__ import annotations

import re
from pathlib import Path

from xian_core.schemas.common import CampaignStatus

ROOT = Path(__file__).resolve().parents[4]


def test_failed_status_is_part_of_enum() -> None:
    assert CampaignStatus.failed == "failed"
    assert "failed" in {s.value for s in CampaignStatus}


def test_router_only_writes_known_statuses() -> None:
    """扫描 campaigns 路由里所有 `campaign.status = "..."` 赋值。"""
    source = (ROOT / "backend" / "services" / "api" / "src" / "xian_api" / "routers" / "campaigns.py").read_text(
        encoding="utf-8"
    )
    written = set(re.findall(r"campaign\.status\s*=\s*[\"']([a-z_]+)[\"']", source))
    assert written, "没有扫到任何状态赋值，正则可能失效了"
    allowed = {s.value for s in CampaignStatus}
    assert written <= allowed, f"写入了枚举外的状态：{written - allowed}"


def test_frontend_labels_cover_every_status() -> None:
    """前端 CAMPAIGN_STATUS_LABEL 必须覆盖后端枚举，否则 Detail 页显示 undefined。"""
    labels = (ROOT / "frontend" / "packages" / "types" / "src" / "enums.ts").read_text(encoding="utf-8")
    block = labels[labels.index("CAMPAIGN_STATUS_LABEL") :]
    block = block[: block.index("};")]
    keys = set(re.findall(r"^\s{2}(\w+)\s*:", block, re.M))
    missing = {s.value for s in CampaignStatus} - keys
    assert not missing, f"前端缺少状态标签：{missing}"