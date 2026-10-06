"""初始建表迁移：PRD 数据字典全量落地（PostgreSQL）。"""

from __future__ import annotations

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """按 Base.metadata 顺序建表；幂等由 create_all checkfirst 保证。"""
    bind = op.get_bind()
    from xian_core.db import models  # noqa: F401
    from xian_core.db.base import Base
    Base.metadata.create_all(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    from xian_core.db import models  # noqa: F401
    from xian_core.db.base import Base
    Base.metadata.drop_all(bind, checkfirst=True)
