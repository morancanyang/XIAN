"""战役等级（grade）契约：SecScore 与等级必须成对落库、成对下发。

背景：执行器原先只写了 ``campaign.sec_score``，漏写 ``campaign.grade``，
导致战役详情环与列表里 SecScore 有值、等级永远是空的。
这里同时锁死「写路径」与「读路径」，避免再出现单边字段。
"""

from __future__ import annotations

import uuid
from pathlib import Path

from xian_core.db.models import Campaign
from xian_core.redteam import execute_campaign
from xian_core.schemas.campaign import CampaignOut
from xian_core.scoring.secscore import GRADE_THRESHOLDS, grade_of

ROOT = Path(__file__).resolve().parents[4]
RUNNER = ROOT / "backend" / "libs" / "xian_core" / "src" / "xian_core" / "redteam" / "runner.py"


def _draft_campaign(tenant_id: uuid.UUID) -> Campaign:
    return Campaign(
        tenant_id=tenant_id,
        agent_id=uuid.uuid4(),
        scope=[],
        intensity="standard",
        budget={},
        constraints={},
        status="attacking",
        judge_mode="standard",
        output_mode="summary",
        preset_id="standard",
    )


async def test_execute_campaign_persists_grade(session, tenant_id) -> None:
    """执行收尾必须把 grade 和 sec_score 一起写进 campaign。"""
    campaign = _draft_campaign(tenant_id)
    session.add(campaign)
    await session.flush()

    result = await execute_campaign(campaign, session=session, tenant_id=tenant_id)
    await session.flush()

    assert campaign.sec_score == result.sec_score
    assert campaign.grade == result.grade
    assert campaign.grade == grade_of(campaign.sec_score)
    assert campaign.grade in {g for _, g in GRADE_THRESHOLDS} | {"D"}


def test_campaign_out_backfills_grade_for_legacy_rows() -> None:
    """历史战役只落了分没落级：读模型按分回推，前端不必自己判断阈值。"""
    out = CampaignOut.model_validate(
        {
            "id": uuid.uuid4(),
            "tenant_id": uuid.uuid4(),
            "agent_id": uuid.uuid4(),
            "scope": [],
            "intensity": "standard",
            "budget": {},
            "constraints": {},
            "judge_mode": "standard",
            "output_mode": "summary",
            "preset_id": "standard",
            "status": "completed",
            "sec_score": 93,
            "grade": None,
            "created_at": "2026-01-01T00:00:00Z",
        }
    )
    assert out.grade == "S"

    out_60 = out.model_copy(update={"sec_score": 60, "grade": None})
    assert CampaignOut.model_validate(out_60).grade == "C"

    out_none = out.model_copy(update={"sec_score": None, "grade": None})
    assert CampaignOut.model_validate(out_none).grade is None


def test_runner_writes_grade_next_to_sec_score() -> None:
    """静态契约：campaign.grade 赋值不能再次从收尾逻辑里消失。"""
    source = RUNNER.read_text(encoding="utf-8")
    assert "campaign.sec_score = result.sec_score" in source
    assert "campaign.grade = result.grade" in source
    assert source.index("campaign.grade = result.grade") < source.index("await _emit(campaign, \"done\"")