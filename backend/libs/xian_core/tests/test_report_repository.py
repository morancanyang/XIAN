"""ReportRepository.for_subject：同一主体只认一份报告，且必须确定性地取到最新版。

背景：两个生成端点早年直接 insert，同主体在库里留了多行报告；
for_subject 原先用 scalar_one_or_none，遇到多行会抛 MultipleResultsFound，
重新生成报告时直接 500。现在查询收敛为"版本最高、最新创建"的单行。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from xian_core.db.models import Report
from xian_core.db.repositories import ReportRepository


def _report(tenant_id: uuid.UUID, subject_id: uuid.UUID, version: int, grade: str) -> Report:
    return Report(
        tenant_id=tenant_id,
        subject_type="campaign",
        subject_id=subject_id,
        version=version,
        grade=grade,
        chapters={"version": version},
    )


async def test_for_subject_returns_the_only_row(session, tenant_id) -> None:
    subject_id = uuid.uuid4()
    repo = ReportRepository(session, tenant_id)
    session.add(_report(tenant_id, subject_id, 1, "C"))
    await session.flush()

    row = await repo.for_subject("campaign", subject_id)

    assert row is not None and row.version == 1
    assert await repo.for_subject("campaign", uuid.uuid4()) is None


async def test_for_subject_picks_highest_version_when_duplicated(session, tenant_id) -> None:
    """存量重复行不能把接口打挂：收敛到版本最高的那一份。"""
    subject_id = uuid.uuid4()
    repo = ReportRepository(session, tenant_id)
    for version, grade in ((1, "C"), (3, "A"), (2, "B")):
        session.add(_report(tenant_id, subject_id, version, grade))
    await session.flush()

    row = await repo.for_subject("campaign", subject_id)

    assert row is not None and row.version == 3, "重复行必须收敛到最高版本"
    assert row.grade == "A"


async def test_for_subject_breaks_ties_by_created_at(session, tenant_id) -> None:
    """同版本重复行按创建时间取最晚，保证同一份数据永远读到同一行。"""
    subject_id = uuid.uuid4()
    repo = ReportRepository(session, tenant_id)
    base = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    older = _report(tenant_id, subject_id, 2, "B")
    older.created_at = base
    newer = _report(tenant_id, subject_id, 2, "A")
    newer.created_at = base + timedelta(hours=1)
    session.add_all([older, newer])
    await session.flush()

    row = await repo.for_subject("campaign", subject_id)

    assert row is not None and row.grade == "A", "同版本必须取创建时间最晚的一行"
