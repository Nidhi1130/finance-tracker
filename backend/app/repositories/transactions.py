from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol
from uuid import UUID, uuid4

import psycopg

from app.repositories.base import InvalidReferenceError, database_session
from app.schemas import TransactionCreate, TransactionOut, TransactionUpdate, TxType

if TYPE_CHECKING:
    from app.repositories.accounts import AccountRepository
    from app.repositories.categories import CategoryRepository


@dataclass
class TransactionRecord:
    id: UUID
    user_id: UUID
    amount: Decimal
    type: TxType
    description: str | None
    date: date
    category_id: UUID | None
    account_id: UUID | None
    created_at: datetime
    updated_at: datetime

    def to_out(self) -> TransactionOut:
        return TransactionOut.model_validate(
            {
                "id": self.id,
                "amount": self.amount,
                "type": self.type,
                "description": self.description,
                "date": self.date,
                "category_id": self.category_id,
                "account_id": self.account_id,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            },
        )


class TransactionRepository(Protocol):
    def list(
        self,
        user_id: UUID,
        *,
        tx_type: TxType | None = None,
        category_id: UUID | None = None,
        account_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[TransactionRecord]: ...

    def create(self, user_id: UUID, payload: TransactionCreate) -> TransactionRecord: ...

    def get(self, user_id: UUID, transaction_id: UUID) -> TransactionRecord | None: ...

    def update(
        self,
        user_id: UUID,
        transaction_id: UUID,
        payload: TransactionUpdate,
    ) -> TransactionRecord | None: ...

    def delete(self, user_id: UUID, transaction_id: UUID) -> bool: ...

    def clear(self) -> None: ...


@dataclass
class InMemoryTransactionRepository:
    _items: dict[UUID, dict[UUID, TransactionRecord]] = field(default_factory=dict)
    category_repository: CategoryRepository | None = None
    account_repository: AccountRepository | None = None

    def list(
        self,
        user_id: UUID,
        *,
        tx_type: TxType | None = None,
        category_id: UUID | None = None,
        account_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[TransactionRecord]:
        records = list(self._items.get(user_id, {}).values())
        filtered: list[TransactionRecord] = []

        for record in records:
            if tx_type and record.type != tx_type:
                continue
            if category_id is not None and record.category_id != category_id:
                continue
            if account_id is not None and record.account_id != account_id:
                continue
            if date_from and record.date < date_from:
                continue
            if date_to and record.date > date_to:
                continue
            filtered.append(record)

        return sorted(filtered, key=lambda item: (item.date, item.created_at), reverse=True)

    def create(self, user_id: UUID, payload: TransactionCreate) -> TransactionRecord:
        self._validate_references(user_id, payload.category_id, payload.account_id)
        now = datetime.now(tz=UTC)
        record = TransactionRecord(
            id=uuid4(),
            user_id=user_id,
            amount=payload.amount,
            type=payload.type,
            description=payload.description,
            date=payload.date,
            category_id=payload.category_id,
            account_id=payload.account_id,
            created_at=now,
            updated_at=now,
        )
        self._items.setdefault(user_id, {})[record.id] = record
        return record

    def get(self, user_id: UUID, transaction_id: UUID) -> TransactionRecord | None:
        return self._items.get(user_id, {}).get(transaction_id)

    def update(
        self,
        user_id: UUID,
        transaction_id: UUID,
        payload: TransactionUpdate,
    ) -> TransactionRecord | None:
        record = self.get(user_id, transaction_id)
        if record is None:
            return None

        data = payload.model_dump(exclude_unset=True)
        self._validate_references(
            user_id,
            data.get("category_id") if "category_id" in data else None,
            data.get("account_id") if "account_id" in data else None,
            validate_category="category_id" in data,
            validate_account="account_id" in data,
        )
        if "amount" in data:
            record.amount = data["amount"]
        if "type" in data:
            record.type = data["type"]
        if "description" in data:
            record.description = data["description"]
        if "date" in data:
            record.date = data["date"]
        if "category_id" in data:
            record.category_id = data["category_id"]
        if "account_id" in data:
            record.account_id = data["account_id"]
        record.updated_at = datetime.now(tz=UTC)
        return record

    def delete(self, user_id: UUID, transaction_id: UUID) -> bool:
        user_items = self._items.get(user_id)
        if not user_items or transaction_id not in user_items:
            return False
        del user_items[transaction_id]
        return True

    def clear(self) -> None:
        self._items.clear()

    def _validate_references(
        self,
        user_id: UUID,
        category_id: UUID | None,
        account_id: UUID | None,
        *,
        validate_category: bool = True,
        validate_account: bool = True,
    ) -> None:
        if (
            validate_category
            and category_id is not None
            and (
                self.category_repository is None
                or not self.category_repository.is_accessible(user_id, category_id)
            )
        ):
            raise InvalidReferenceError("category_id")
        if (
            validate_account
            and account_id is not None
            and (
                self.account_repository is None
                or not self.account_repository.is_accessible(user_id, account_id)
            )
        ):
            raise InvalidReferenceError("account_id")

    def clear_category_reference(self, user_id: UUID, category_id: UUID) -> None:
        for record in self._items.get(user_id, {}).values():
            if record.category_id == category_id:
                record.category_id = None
                record.updated_at = datetime.now(tz=UTC)

    def clear_account_reference(self, user_id: UUID, account_id: UUID) -> None:
        for record in self._items.get(user_id, {}).values():
            if record.account_id == account_id:
                record.account_id = None
                record.updated_at = datetime.now(tz=UTC)


@dataclass
class PostgresTransactionRepository:
    database_url: str

    @staticmethod
    def _record_from_row(row: dict[str, object]) -> TransactionRecord:
        return TransactionRecord(
            id=UUID(str(row["id"])),
            user_id=UUID(str(row["user_id"])),
            amount=row["amount"],
            type=TxType(str(row["type"])),
            description=row["description"],
            date=row["date"],
            category_id=UUID(str(row["category_id"])) if row["category_id"] else None,
            account_id=UUID(str(row["account_id"])) if row["account_id"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_out(row: dict[str, object]) -> TransactionOut:
        return TransactionOut.model_validate(
            {
                "id": UUID(str(row["id"])),
                "amount": row["amount"],
                "type": TxType(str(row["type"])),
                "description": row["description"],
                "date": row["date"],
                "category_id": UUID(str(row["category_id"])) if row["category_id"] else None,
                "account_id": UUID(str(row["account_id"])) if row["account_id"] else None,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
        )

    def list(
        self,
        user_id: UUID,
        *,
        tx_type: TxType | None = None,
        category_id: UUID | None = None,
        account_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[TransactionRecord]:
        conditions = ["user_id = current_setting('app.user_id')::uuid"]
        params: list[object] = []

        if tx_type is not None:
            conditions.append("type = %s")
            params.append(tx_type.value)
        if category_id is not None:
            conditions.append("category_id = %s")
            params.append(category_id)
        if account_id is not None:
            conditions.append("account_id = %s")
            params.append(account_id)
        if date_from is not None:
            conditions.append("date >= %s")
            params.append(date_from)
        if date_to is not None:
            conditions.append("date <= %s")
            params.append(date_to)

        query = f"""
            select id, user_id, amount, type, description, date,
                   category_id, account_id, created_at, updated_at
            from transactions
            where {" and ".join(conditions)}
            order by date desc, created_at desc
        """

        with database_session(self.database_url, user_id) as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._record_from_row(row) for row in rows]

    def create(self, user_id: UUID, payload: TransactionCreate) -> TransactionRecord:
        query = """
            insert into transactions (
                id,
                user_id,
                amount,
                type,
                description,
                date,
                category_id,
                account_id
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            returning id, user_id, amount, type, description, date,
                      category_id, account_id, created_at, updated_at
        """

        params = (
            uuid4(),
            user_id,
            payload.amount,
            payload.type.value,
            payload.description,
            payload.date,
            payload.category_id,
            payload.account_id,
        )
        try:
            with database_session(self.database_url, user_id) as connection:
                self._validate_references(
                    connection,
                    user_id,
                    payload.category_id,
                    payload.account_id,
                )
                row = connection.execute(query, params).fetchone()
        except psycopg.errors.CheckViolation as error:
            raise self._reference_error(error) from error
        assert row is not None
        return self._record_from_row(row)

    def get(self, user_id: UUID, transaction_id: UUID) -> TransactionRecord | None:
        query = """
            select id, user_id, amount, type, description, date,
                   category_id, account_id, created_at, updated_at
            from transactions
            where id = %s and user_id = current_setting('app.user_id')::uuid
        """
        with database_session(self.database_url, user_id) as connection:
            row = connection.execute(query, (transaction_id,)).fetchone()
        if row is None:
            return None
        return self._record_from_row(row)

    def update(
        self,
        user_id: UUID,
        transaction_id: UUID,
        payload: TransactionUpdate,
    ) -> TransactionRecord | None:
        data = payload.model_dump(exclude_unset=True)
        if not data:
            return self.get(user_id, transaction_id)

        assignments: list[str] = []
        params: list[object] = []

        if "amount" in data:
            assignments.append("amount = %s")
            params.append(data["amount"])
        if "type" in data:
            assignments.append("type = %s")
            params.append(data["type"].value)
        if "description" in data:
            assignments.append("description = %s")
            params.append(data["description"])
        if "date" in data:
            assignments.append("date = %s")
            params.append(data["date"])
        if "category_id" in data:
            assignments.append("category_id = %s")
            params.append(data["category_id"])
        if "account_id" in data:
            assignments.append("account_id = %s")
            params.append(data["account_id"])

        assignments.append("updated_at = now()")
        params.extend([transaction_id, user_id])

        query = f"""
            update transactions
            set {", ".join(assignments)}
            where id = %s and user_id = %s
            returning id, user_id, amount, type, description, date,
                      category_id, account_id, created_at, updated_at
        """
        try:
            with database_session(self.database_url, user_id) as connection:
                self._validate_references(
                    connection,
                    user_id,
                    data.get("category_id") if "category_id" in data else None,
                    data.get("account_id") if "account_id" in data else None,
                    validate_category="category_id" in data,
                    validate_account="account_id" in data,
                )
                row = connection.execute(query, params).fetchone()
        except psycopg.errors.CheckViolation as error:
            raise self._reference_error(error) from error
        if row is None:
            return None
        return self._record_from_row(row)

    def delete(self, user_id: UUID, transaction_id: UUID) -> bool:
        query = """
            delete from transactions
            where id = %s and user_id = current_setting('app.user_id')::uuid
        """
        with database_session(self.database_url, user_id) as connection:
            result = connection.execute(query, (transaction_id,))
        return result.rowcount > 0

    def clear(self) -> None:
        with psycopg.connect(self.database_url) as connection, connection.transaction():
            connection.execute("delete from transactions")

    @staticmethod
    def _validate_references(
        connection,
        user_id: UUID,
        category_id: UUID | None,
        account_id: UUID | None,
        *,
        validate_category: bool = True,
        validate_account: bool = True,
    ) -> None:
        if validate_category and category_id is not None:
            allowed = connection.execute(
                """
                select exists(
                    select 1 from categories
                    where id = %s and (user_id is null or user_id = %s)
                )
                """,
                (category_id, user_id),
            ).fetchone()["exists"]
            if not allowed:
                raise InvalidReferenceError("category_id")
        if validate_account and account_id is not None:
            allowed = connection.execute(
                "select exists(select 1 from accounts where id = %s and user_id = %s)",
                (account_id, user_id),
            ).fetchone()["exists"]
            if not allowed:
                raise InvalidReferenceError("account_id")

    @staticmethod
    def _reference_error(error: psycopg.errors.CheckViolation) -> InvalidReferenceError:
        field = "category_id" if "category_id" in str(error) else "account_id"
        return InvalidReferenceError(field)


def build_transaction_repository() -> TransactionRepository:
    from os import getenv

    database_url = getenv("DATABASE_URL")
    if database_url:
        return PostgresTransactionRepository(database_url)
    return InMemoryTransactionRepository()
