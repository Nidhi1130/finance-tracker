from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

import psycopg

from app.repositories.base import DuplicateResourceError, database_session
from app.schemas import AccountCreate, AccountOut, AccountUpdate


@dataclass
class AccountRecord:
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime

    def to_out(self) -> AccountOut:
        return AccountOut(id=self.id, name=self.name, created_at=self.created_at)


class AccountRepository(Protocol):
    def list(self, user_id: UUID) -> list[AccountRecord]: ...

    def create(self, user_id: UUID, payload: AccountCreate) -> AccountRecord: ...

    def get(self, user_id: UUID, account_id: UUID) -> AccountRecord | None: ...

    def update(
        self,
        user_id: UUID,
        account_id: UUID,
        payload: AccountUpdate,
    ) -> AccountRecord | None: ...

    def delete(self, user_id: UUID, account_id: UUID) -> bool: ...

    def clear(self) -> None: ...


@dataclass
class InMemoryAccountRepository:
    _items: dict[UUID, dict[UUID, AccountRecord]] = field(default_factory=dict)

    def list(self, user_id: UUID) -> list[AccountRecord]:
        return sorted(
            self._items.get(user_id, {}).values(),
            key=lambda item: item.name.casefold(),
        )

    def _is_duplicate(self, user_id: UUID, name: str, exclude: UUID | None = None) -> bool:
        return any(
            record.id != exclude and record.name.casefold() == name.casefold()
            for record in self._items.get(user_id, {}).values()
        )

    def create(self, user_id: UUID, payload: AccountCreate) -> AccountRecord:
        if self._is_duplicate(user_id, payload.name):
            raise DuplicateResourceError
        record = AccountRecord(
            id=uuid4(),
            user_id=user_id,
            name=payload.name,
            created_at=datetime.now(tz=timezone.utc),
        )
        self._items.setdefault(user_id, {})[record.id] = record
        return record

    def get(self, user_id: UUID, account_id: UUID) -> AccountRecord | None:
        return self._items.get(user_id, {}).get(account_id)

    def update(
        self,
        user_id: UUID,
        account_id: UUID,
        payload: AccountUpdate,
    ) -> AccountRecord | None:
        record = self.get(user_id, account_id)
        if record is None:
            return None
        if self._is_duplicate(user_id, payload.name, exclude=account_id):
            raise DuplicateResourceError
        record.name = payload.name
        return record

    def delete(self, user_id: UUID, account_id: UUID) -> bool:
        records = self._items.get(user_id, {})
        if account_id not in records:
            return False
        del records[account_id]
        return True

    def clear(self) -> None:
        self._items.clear()


@dataclass
class PostgresAccountRepository:
    database_url: str

    @staticmethod
    def _record(row: dict[str, object]) -> AccountRecord:
        return AccountRecord(
            id=UUID(str(row["id"])),
            user_id=UUID(str(row["user_id"])),
            name=str(row["name"]),
            created_at=row["created_at"],
        )

    def list(self, user_id: UUID) -> list[AccountRecord]:
        with database_session(self.database_url, user_id) as connection:
            rows = connection.execute(
                """
                select id, user_id, name, created_at
                from accounts where user_id = %s order by lower(name)
                """,
                (user_id,),
            ).fetchall()
        return [self._record(row) for row in rows]

    def create(self, user_id: UUID, payload: AccountCreate) -> AccountRecord:
        try:
            with database_session(self.database_url, user_id) as connection:
                row = connection.execute(
                    """
                    insert into accounts (id, user_id, name)
                    values (%s, %s, %s)
                    returning id, user_id, name, created_at
                    """,
                    (uuid4(), user_id, payload.name),
                ).fetchone()
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateResourceError from error
        assert row is not None
        return self._record(row)

    def get(self, user_id: UUID, account_id: UUID) -> AccountRecord | None:
        with database_session(self.database_url, user_id) as connection:
            row = connection.execute(
                """
                select id, user_id, name, created_at
                from accounts where id = %s and user_id = %s
                """,
                (account_id, user_id),
            ).fetchone()
        return self._record(row) if row else None

    def update(
        self,
        user_id: UUID,
        account_id: UUID,
        payload: AccountUpdate,
    ) -> AccountRecord | None:
        try:
            with database_session(self.database_url, user_id) as connection:
                row = connection.execute(
                    """
                    update accounts set name = %s
                    where id = %s and user_id = %s
                    returning id, user_id, name, created_at
                    """,
                    (payload.name, account_id, user_id),
                ).fetchone()
        except psycopg.errors.UniqueViolation as error:
            raise DuplicateResourceError from error
        return self._record(row) if row else None

    def delete(self, user_id: UUID, account_id: UUID) -> bool:
        with database_session(self.database_url, user_id) as connection:
            result = connection.execute(
                "delete from accounts where id = %s and user_id = %s",
                (account_id, user_id),
            )
        return result.rowcount > 0

    def clear(self) -> None:
        return None
