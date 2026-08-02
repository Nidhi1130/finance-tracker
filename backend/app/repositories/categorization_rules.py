from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol
from uuid import UUID, uuid4

import psycopg

from app.repositories.base import DuplicateResourceError, InvalidReferenceError, database_session
from app.schemas import (
    CategorizationRuleCreate,
    CategorizationRuleOut,
    CategorizationRuleUpdate,
)

if TYPE_CHECKING:
    from app.repositories.categories import CategoryRecord, CategoryRepository


@dataclass
class CategorizationRuleRecord:
    id: UUID
    user_id: UUID
    keyword: str
    category_id: UUID
    category_name: str
    category_color: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    def to_out(self) -> CategorizationRuleOut:
        return CategorizationRuleOut.model_validate(
            {
                "id": self.id,
                "keyword": self.keyword,
                "category_id": self.category_id,
                "category_name": self.category_name,
                "category_color": self.category_color,
                "enabled": self.enabled,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            },
        )


class CategorizationRuleRepository(Protocol):
    def list(
        self,
        user_id: UUID,
        *,
        enabled_only: bool = False,
    ) -> list[CategorizationRuleRecord]: ...

    def create(
        self,
        user_id: UUID,
        payload: CategorizationRuleCreate,
    ) -> CategorizationRuleRecord: ...

    def get(self, user_id: UUID, rule_id: UUID) -> CategorizationRuleRecord | None: ...

    def update(
        self,
        user_id: UUID,
        rule_id: UUID,
        payload: CategorizationRuleUpdate,
    ) -> CategorizationRuleRecord | None: ...

    def delete(self, user_id: UUID, rule_id: UUID) -> bool: ...

    def clear(self) -> None: ...


@dataclass
class InMemoryCategorizationRuleRepository:
    category_repository: CategoryRepository | None = None
    _items: dict[UUID, dict[UUID, CategorizationRuleRecord]] = field(default_factory=dict)

    def list(
        self,
        user_id: UUID,
        *,
        enabled_only: bool = False,
    ) -> list[CategorizationRuleRecord]:
        records = [
            decorated
            for record in list(self._items.get(user_id, {}).values())
            if (decorated := self._with_category(user_id, record)) is not None
            and (not enabled_only or decorated.enabled)
        ]
        return sorted(records, key=lambda record: (record.keyword.casefold(), str(record.id)))

    def create(
        self,
        user_id: UUID,
        payload: CategorizationRuleCreate,
    ) -> CategorizationRuleRecord:
        category = self._require_category(user_id, payload.category_id)
        if self._is_duplicate(user_id, payload.keyword):
            raise DuplicateResourceError
        now = datetime.now(tz=timezone.utc)
        record = CategorizationRuleRecord(
            id=uuid4(),
            user_id=user_id,
            keyword=payload.keyword,
            category_id=payload.category_id,
            category_name=category.name,
            category_color=category.color,
            enabled=payload.enabled,
            created_at=now,
            updated_at=now,
        )
        self._items.setdefault(user_id, {})[record.id] = record
        return record

    def get(self, user_id: UUID, rule_id: UUID) -> CategorizationRuleRecord | None:
        record = self._available_record(user_id, rule_id)
        return self._with_category(user_id, record) if record else None

    def update(
        self,
        user_id: UUID,
        rule_id: UUID,
        payload: CategorizationRuleUpdate,
    ) -> CategorizationRuleRecord | None:
        record = self._available_record(user_id, rule_id)
        if record is None:
            return None
        data = payload.model_dump(exclude_unset=True)
        keyword = data.get("keyword", record.keyword)
        if keyword is not None and self._is_duplicate(user_id, keyword, exclude=rule_id):
            raise DuplicateResourceError
        category_id = data.get("category_id", record.category_id)
        if category_id is None:
            raise InvalidReferenceError("category_id")
        category = self._require_category(user_id, category_id)
        if "keyword" in data:
            record.keyword = keyword
        if "category_id" in data:
            record.category_id = category_id
        if "enabled" in data:
            record.enabled = data["enabled"]
        record.category_name = category.name
        record.category_color = category.color
        record.updated_at = datetime.now(tz=timezone.utc)
        return record

    def delete(self, user_id: UUID, rule_id: UUID) -> bool:
        records = self._items.get(user_id, {})
        if self._available_record(user_id, rule_id) is None:
            return False
        del records[rule_id]
        return True

    def clear(self) -> None:
        self._items.clear()

    def _is_duplicate(self, user_id: UUID, keyword: str, exclude: UUID | None = None) -> bool:
        return any(
            record.id != exclude and record.keyword.casefold() == keyword.casefold()
            for record in self._items.get(user_id, {}).values()
        )

    def _require_category(self, user_id: UUID, category_id: UUID) -> CategoryRecord:
        if self.category_repository is None:
            raise InvalidReferenceError("category_id")
        category = self.category_repository.get(user_id, category_id)
        if category is None:
            raise InvalidReferenceError("category_id")
        return category

    def _available_record(
        self,
        user_id: UUID,
        rule_id: UUID,
    ) -> CategorizationRuleRecord | None:
        record = self._items.get(user_id, {}).get(rule_id)
        if record is None:
            return None
        if self.category_repository is None or (
            self.category_repository.get(user_id, record.category_id) is None
        ):
            self._items.get(user_id, {}).pop(rule_id, None)
            return None
        return record

    def _with_category(
        self,
        user_id: UUID,
        record: CategorizationRuleRecord,
    ) -> CategorizationRuleRecord | None:
        if self.category_repository is None:
            return None
        category = self.category_repository.get(user_id, record.category_id)
        if category is None:
            self._items.get(user_id, {}).pop(record.id, None)
            return None
        return replace(
            record,
            category_name=category.name,
            category_color=category.color,
        )


@dataclass
class PostgresCategorizationRuleRepository:
    database_url: str

    _FIELDS = """
        r.id, r.user_id, r.keyword, r.category_id, c.name as category_name,
        c.color as category_color, r.enabled, r.created_at, r.updated_at
    """

    @staticmethod
    def _record(row: dict[str, object]) -> CategorizationRuleRecord:
        return CategorizationRuleRecord(
            id=UUID(str(row["id"])),
            user_id=UUID(str(row["user_id"])),
            keyword=str(row["keyword"]),
            category_id=UUID(str(row["category_id"])),
            category_name=str(row["category_name"]),
            category_color=str(row["category_color"]),
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list(
        self,
        user_id: UUID,
        *,
        enabled_only: bool = False,
    ) -> list[CategorizationRuleRecord]:
        enabled_clause = "and r.enabled" if enabled_only else ""
        with database_session(self.database_url, user_id) as connection:
            rows = connection.execute(
                f"""
                select {self._FIELDS}
                from categorization_rules r
                join categories c on c.id = r.category_id
                where r.user_id = %s {enabled_clause}
                order by lower(r.keyword), r.id
                """,
                (user_id,),
            ).fetchall()
        return [self._record(row) for row in rows]

    def create(
        self,
        user_id: UUID,
        payload: CategorizationRuleCreate,
    ) -> CategorizationRuleRecord:
        try:
            with database_session(self.database_url, user_id) as connection:
                self._require_category(connection, user_id, payload.category_id)
                row = connection.execute(
                    f"""
                    with inserted as (
                        insert into categorization_rules (id, user_id, keyword, category_id, enabled)
                        values (%s, %s, %s, %s, %s)
                        returning *
                    )
                    select {self._FIELDS.replace('r.', 'inserted.')}
                    from inserted
                    join categories c on c.id = inserted.category_id
                    """,
                    (uuid4(), user_id, payload.keyword, payload.category_id, payload.enabled),
                ).fetchone()
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateResourceError from error
        assert row is not None
        return self._record(row)

    def get(self, user_id: UUID, rule_id: UUID) -> CategorizationRuleRecord | None:
        with database_session(self.database_url, user_id) as connection:
            row = connection.execute(
                f"""
                select {self._FIELDS}
                from categorization_rules r
                join categories c on c.id = r.category_id
                where r.id = %s and r.user_id = %s
                """,
                (rule_id, user_id),
            ).fetchone()
        return self._record(row) if row else None

    def update(
        self,
        user_id: UUID,
        rule_id: UUID,
        payload: CategorizationRuleUpdate,
    ) -> CategorizationRuleRecord | None:
        data = payload.model_dump(exclude_unset=True)
        try:
            with database_session(self.database_url, user_id) as connection:
                current = connection.execute(
                    """
                    select id, keyword, category_id, enabled
                    from categorization_rules
                    where id = %s and user_id = %s
                    """,
                    (rule_id, user_id),
                ).fetchone()
                if current is None:
                    return None

                category_id = data.get("category_id", current["category_id"])
                if category_id is None:
                    raise InvalidReferenceError("category_id")
                self._require_category(connection, user_id, category_id)

                row = connection.execute(
                    f"""
                    with updated as (
                        update categorization_rules
                        set keyword = %s,
                            category_id = %s,
                            enabled = %s,
                            updated_at = now()
                        where id = %s and user_id = %s
                        returning *
                    )
                    select {self._FIELDS.replace('r.', 'updated.')}
                    from updated
                    join categories c on c.id = updated.category_id
                    """,
                    (
                        data.get("keyword", current["keyword"]),
                        category_id,
                        data.get("enabled", current["enabled"]),
                        rule_id,
                        user_id,
                    ),
                ).fetchone()
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateResourceError from error
        assert row is not None
        return self._record(row)

    def delete(self, user_id: UUID, rule_id: UUID) -> bool:
        with database_session(self.database_url, user_id) as connection:
            result = connection.execute(
                "delete from categorization_rules where id = %s and user_id = %s",
                (rule_id, user_id),
            )
        return result.rowcount > 0

    def clear(self) -> None:
        return None

    @staticmethod
    def _require_category(connection, user_id: UUID, category_id: UUID) -> None:
        row = connection.execute(
            """
            select id from categories
            where id = %s and (user_id is null or user_id = %s)
            """,
            (category_id, user_id),
        ).fetchone()
        if row is None:
            raise InvalidReferenceError("category_id")
