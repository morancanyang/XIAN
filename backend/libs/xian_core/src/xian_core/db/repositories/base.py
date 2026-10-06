"""仓储基类：所有带 tenant_id 的查询由本层统一注入隔离条件（技术方案 6.2.1 / 9.2）。"""

from __future__ import annotations

import uuid
from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...errors import NotFoundError
from ..base import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository[ModelT]:
    model: type[ModelT]

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None) -> None:
        self.session = session
        self.tenant_id = tenant_id

    # ---------------------------------------------------------------- helpers
    def _base_query(self) -> Select:
        stmt = select(self.model)
        if self.tenant_id is not None and hasattr(self.model, "tenant_id"):
            stmt = stmt.where(self.model.tenant_id == self.tenant_id)  # type: ignore[attr-defined]
        return stmt

    async def get(self, entity_id: uuid.UUID) -> ModelT:
        obj = await self.session.get(self.model, entity_id)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} {entity_id} 不存在")
        if self.tenant_id is not None and getattr(obj, "tenant_id", None) not in (None, self.tenant_id):
            raise NotFoundError(f"{self.model.__name__} {entity_id} 不存在")
        return obj

    async def get_optional(self, entity_id: uuid.UUID) -> ModelT | None:
        try:
            return await self.get(entity_id)
        except NotFoundError:
            return None

    async def list(
        self,
        *,
        keyword: str | None = None,
        keyword_fields: tuple[str, ...] = (),
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        desc: bool = True,
        limit: int | None = None,
    ) -> list[ModelT]:
        stmt = self._apply_filters(keyword, keyword_fields, filters)
        if order_by:
            column = getattr(self.model, order_by, None)
            if column is not None:
                stmt = stmt.order_by(column.desc() if desc else column.asc())
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)

    async def paginate(
        self,
        *,
        page: int = 1,
        size: int = 20,
        keyword: str | None = None,
        keyword_fields: tuple[str, ...] = (),
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        desc: bool = True,
    ) -> tuple[list[ModelT], int]:
        stmt = self._apply_filters(keyword, keyword_fields, filters)
        if filters:
            for field, value in filters.items():
                if value is None:
                    continue
                column = getattr(self.model, field, None)
                if column is None:
                    continue
                if isinstance(value, (list, tuple, set)):
                    stmt = stmt.where(column.in_(list(value)))
                else:
                    stmt = stmt.where(column == value)
        count_stmt = stmt.with_only_columns(func.count()).order_by(None)
        total = (await self.session.execute(count_stmt)).scalar_one()
        if order_by:
            column = getattr(self.model, order_by, None)
            if column is not None:
                stmt = stmt.order_by(column.desc() if desc else column.asc())
        stmt = stmt.limit(size).offset((page - 1) * size)
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows), int(total)

    def _apply_filters(
        self,
        keyword: str | None = None,
        keyword_fields: tuple[str, ...] = (),
        filters: dict[str, Any] | None = None,
    ):
        stmt = self._base_query()
        if keyword and keyword_fields:
            from sqlalchemy import or_

            clauses = []
            for field in keyword_fields:
                column = getattr(self.model, field, None)
                if column is not None:
                    clauses.append(column.ilike(f"%{keyword}%"))
            if clauses:
                stmt = stmt.where(or_(*clauses))
        if filters:
            for field, value in filters.items():
                if value is None:
                    continue
                column = getattr(self.model, field, None)
                if column is None:
                    continue
                if isinstance(value, (list, tuple, set)):
                    stmt = stmt.where(column.in_(list(value)))
                else:
                    stmt = stmt.where(column == value)
        return stmt

    async def list_by_id(self, entity_id: uuid.UUID) -> list[ModelT]:
        """按主键查询并强制租户隔离；无权限时返回空列表而非泄露存在性。"""
        stmt = self._base_query().where(self.model.id == entity_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by(self, **filters: Any) -> list[ModelT]:
        stmt = self._base_query()
        for field, value in filters.items():
            column = getattr(self.model, field, None)
            if column is not None:
                stmt = stmt.where(column == value)
        return list((await self.session.execute(stmt)).scalars().all())

    async def update_fields(self, entity: ModelT, fields: dict[str, Any]) -> ModelT:
        for key, value in fields.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        await self.session.flush()
        return entity

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def count(self) -> int:
        stmt = self._base_query().with_only_columns(func.count()).order_by(None)
        return int((await self.session.execute(stmt)).scalar_one())