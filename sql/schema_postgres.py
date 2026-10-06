#!/usr/bin/env python3
"""从 ORM 元数据生成可直接执行的 PostgreSQL 建表 SQL。

保持 SQL 与 `xian_core.db.models` 永远一致 —— 任何模型改动后重跑本脚本即可：

    python sql/schema_postgres.py            # 写出 sql/schema.postgres.sql

输出文件已被 `sql/` 目录的部署文档引用；不要在生成物上手改。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend" / "libs" / "xian_core" / "src"))

from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
from xian_core.db.base import Base  # noqa: E402

HEADER = """-- ============================================================================
-- XIAN · AI Agent 红蓝对抗平台 —— PostgreSQL 全量建表脚本
-- 由 sql/schema_postgres.py 从 xian_core.db.models.Base.metadata 自动生成
-- 生成器：python sql/schema_postgres.py   （以确保 SQL 与 ORM 永远一致）
-- 兼容 PostgreSQL 16；仅依赖 gen_random_uuid() 与 CITEXT 之外的 PG 内建类型
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()

"""


def render() -> str:
    dialect = postgresql.dialect()
    chunks: list[str] = [HEADER]
    for _, table in Base.metadata.tables.items():
        chunks.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";\n")
        for index in table.indexes:
            chunks.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
        chunks.append("")
    return "\n".join(chunks)


def main() -> int:
    text = render()
    out = HERE / "schema.postgres.sql"
    out.write_text(text, encoding="utf-8")
    tables = len(Base.metadata.tables)
    indexes = sum(len(t.indexes) for t in Base.metadata.tables.values())
    fks = sum(len(t.foreign_keys) for t in Base.metadata.tables.values())
    print(f"written {out}（{tables} tables / {indexes} indexes / {fks} foreign keys）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
