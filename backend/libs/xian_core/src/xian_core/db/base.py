"""SQLAlchemy 2.0 基类与混入：所有实体统一走 ``tenant_id`` 隔离键（技术方案 6.2.1）。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, TextClause, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import CHAR, TypeDecorator


def timestamp_default() -> TextClause:
    """跨方言时间戳默认值：PG 走 now()，SQLite 走 CURRENT_TIMESTAMP。"""
    from sqlalchemy import text

    return text("CURRENT_TIMESTAMP" if _is_sqlite() else "now()")


def _is_sqlite() -> bool:
    from ..config import settings

    return settings.db.dsn.startswith("sqlite")


class GUID(TypeDecorator):
    """跨库可用的 UUID 类型（PG 用原生 uuid，其他库退化为 CHAR(36)）。"""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class JSONType(TypeDecorator):
    """跨库 JSON 列。"""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB

            return dialect.type_descriptor(JSONB())
        from sqlalchemy import JSON

        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        import json

        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, default=str)

    def process_result_value(self, value, dialect):
        if value is None or not isinstance(value, str):
            return value
        import json

        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value


class StringArray(TypeDecorator):
    """跨库字符串数组列。"""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import ARRAY

            return dialect.type_descriptor(ARRAY(__import__("sqlalchemy").String))
        return dialect.type_descriptor(CHAR(1024))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        import json

        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        if value is None or not isinstance(value, str):
            return value
        import json

        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class UUIDPK:
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class TenantMixin:
    """租户隔离键：repository 层统一注入查询条件（技术方案 6.2.1 多租户隔离要求）。"""

    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)