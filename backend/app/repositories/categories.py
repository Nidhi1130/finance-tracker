from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

import psycopg

from app.repositories.base import (
    DuplicateResourceError,
    ForbiddenResourceError,
    database_session,
)
from app.schemas import CategoryCreate, CategoryOut, CategoryUpdate

DEFAULT_CATEGORIES = (
    (UUID("00000000-0000-4000-8000-000000000001"), "Housing", "#7C3AED"),
    (UUID("00000000-0000-4000-8000-000000000002"), "Groceries", "#16A34A"),
    (UUID("00000000-0000-4000-8000-000000000003"), "Dining", "#EA580C"),
    (UUID("00000000-0000-4000-8000-000000000004"), "Transport", "#2563EB"),
    (UUID("00000000-0000-4000-8000-000000000005"), "Utilities", "#0891B2"),
    (UUID("00000000-0000-4000-8000-000000000006"), "Health", "#DC2626"),
    (UUID("00000000-0000-4000-8000-000000000007"), "Entertainment", "#DB2777"),
    (UUID("00000000-0000-4000-8000-000000000008"), "Shopping", "#CA8A04"),
    (UUID("00000000-0000-4000-8000-000000000009"), "Salary", "#059669"),
    (UUID("00000000-0000-4000-8000-000000000010"), "Other", "#6B7280"),
)


@dataclass
class CategoryRecord:
    id: UUID
    user_id: UUID | None
    name: str
    color: str
    created_at: datetime

    def to_out(self) -> CategoryOut:
        return CategoryOut(
            id=self.id,
            name=self.name,
            color=self.color,
            is_global=self.user_id is None,
            created_at=self.created_at,
        )


class CategoryRepository(Protocol):
    def list(self, user_id: UUID) -> list[CategoryRecord]: ...

    def create(self, user_id: UUID, payload: CategoryCreate) -> CategoryRecord: ...

    def get(self, user_id: UUID, category_id: UUID) -> CategoryRecord | None: ...

    def update(
        self,
        user_id: UUID,
        category_id: UUID,
        payload: CategoryUpdate,
    ) -> CategoryRecord | None: ...

    def delete(self, user_id: UUID, category_id: UUID) -> bool: ...

    def is_accessible(self, user_id: UUID, category_id: UUID) -> bool: ...

    def clear(self) -> None: ...


@dataclass
class InMemoryCategoryRepository:
    _items: dict[UUID, dict[UUID, CategoryRecord]] = field(default_factory=dict)
    _globals: dict[UUID, CategoryRecord] = field(init=False)
    _on_delete: Callable[[UUID, UUID], None] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        created_at = datetime(2026, 1, 1, tzinfo=UTC)
        self._globals = {
            category_id: CategoryRecord(
                id=category_id,
                user_id=None,
                name=name,
                color=color,
                created_at=created_at,
            )
            for category_id, name, color in DEFAULT_CATEGORIES
        }

    def list(self, user_id: UUID) -> list[CategoryRecord]:
        records = [*self._globals.values(), *self._items.get(user_id, {}).values()]
        return sorted(records, key=lambda item: (item.user_id is not None, item.name.casefold()))

    def _is_duplicate(self, user_id: UUID, name: str, exclude: UUID | None = None) -> bool:
        return any(
            record.id != exclude and record.name.casefold() == name.casefold()
            for record in self._items.get(user_id, {}).values()
        )

    def create(self, user_id: UUID, payload: CategoryCreate) -> CategoryRecord:
        if self._is_duplicate(user_id, payload.name):
            raise DuplicateResourceError
        record = CategoryRecord(
            id=uuid4(),
            user_id=user_id,
            name=payload.name,
            color=payload.color,
            created_at=datetime.now(tz=UTC),
        )
        self._items.setdefault(user_id, {})[record.id] = record
        return record

    def get(self, user_id: UUID, category_id: UUID) -> CategoryRecord | None:
        return self._globals.get(category_id) or self._items.get(user_id, {}).get(category_id)

    def update(
        self,
        user_id: UUID,
        category_id: UUID,
        payload: CategoryUpdate,
    ) -> CategoryRecord | None:
        if category_id in self._globals:
            raise ForbiddenResourceError
        record = self._items.get(user_id, {}).get(category_id)
        if record is None:
            return None
        if self._is_duplicate(user_id, payload.name, exclude=category_id):
            raise DuplicateResourceError
        record.name = payload.name
        record.color = payload.color
        return record

    def delete(self, user_id: UUID, category_id: UUID) -> bool:
        if category_id in self._globals:
            raise ForbiddenResourceError
        records = self._items.get(user_id, {})
        if category_id not in records:
            return False
        del records[category_id]
        if self._on_delete is not None:
            self._on_delete(user_id, category_id)
        return True

    def is_accessible(self, user_id: UUID, category_id: UUID) -> bool:
        return self.get(user_id, category_id) is not None

    def set_delete_callback(self, callback: Callable[[UUID, UUID], None]) -> None:
        self._on_delete = callback

    def clear(self) -> None:
        self._items.clear()


@dataclass
class PostgresCategoryRepository:
    database_url: str

    @staticmethod
    def _record(row: dict[str, object]) -> CategoryRecord:
        return CategoryRecord(
            id=UUID(str(row["id"])),
            user_id=UUID(str(row["user_id"])) if row["user_id"] else None,
            name=str(row["name"]),
            color=str(row["color"]),
            created_at=row["created_at"],
        )

    def list(self, user_id: UUID) -> list[CategoryRecord]:
        with database_session(self.database_url, user_id) as connection:
            rows = connection.execute(
                """
                select id, user_id, name, color, created_at
                from categories
                where user_id is null or user_id = %s
                order by (user_id is not null), lower(name)
                """,
                (user_id,),
            ).fetchall()
        return [self._record(row) for row in rows]

    def create(self, user_id: UUID, payload: CategoryCreate) -> CategoryRecord:
        try:
            with database_session(self.database_url, user_id) as connection:
                row = connection.execute(
                    """
                    insert into categories (id, user_id, name, color)
                    values (%s, %s, %s, %s)
                    returning id, user_id, name, color, created_at
                    """,
                    (uuid4(), user_id, payload.name, payload.color),
                ).fetchone()
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateResourceError from error
        assert row is not None
        return self._record(row)

    def get(self, user_id: UUID, category_id: UUID) -> CategoryRecord | None:
        with database_session(self.database_url, user_id) as connection:
            row = connection.execute(
                """
                select id, user_id, name, color, created_at
                from categories
                where id = %s and (user_id is null or user_id = %s)
                """,
                (category_id, user_id),
            ).fetchone()
        return self._record(row) if row else None

    def update(
        self,
        user_id: UUID,
        category_id: UUID,
        payload: CategoryUpdate,
    ) -> CategoryRecord | None:
        current = self.get(user_id, category_id)
        if current is not None and current.user_id is None:
            raise ForbiddenResourceError
        try:
            with database_session(self.database_url, user_id) as connection:
                row = connection.execute(
                    """
                    update categories set name = %s, color = %s
                    where id = %s and user_id = %s
                    returning id, user_id, name, color, created_at
                    """,
                    (payload.name, payload.color, category_id, user_id),
                ).fetchone()
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateResourceError from error
        return self._record(row) if row else None

    def delete(self, user_id: UUID, category_id: UUID) -> bool:
        current = self.get(user_id, category_id)
        if current is not None and current.user_id is None:
            raise ForbiddenResourceError
        with database_session(self.database_url, user_id) as connection:
            result = connection.execute(
                "delete from categories where id = %s and user_id = %s",
                (category_id, user_id),
            )
        return result.rowcount > 0

    def is_accessible(self, user_id: UUID, category_id: UUID) -> bool:
        return self.get(user_id, category_id) is not None

    def clear(self) -> None:
        return None
