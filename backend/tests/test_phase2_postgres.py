from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Self
from uuid import UUID

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

from app.repositories.accounts import PostgresAccountRepository
from app.repositories.base import InvalidReferenceError, database_session
from app.repositories.categories import PostgresCategoryRepository
from app.repositories.dashboard import PostgresDashboardRepository
from app.repositories.transactions import PostgresTransactionRepository
from app.schemas import (
    AccountCreate,
    CategoryCreate,
    DashboardBucket,
    TransactionCreate,
    TxType,
)

ROOT = Path(__file__).parents[2]
INIT_SQL = (ROOT / "backend/sql/init.sql").read_text()
MIGRATION_SQL = (ROOT / "backend/sql/migrations/003_phase_3_dashboard_index.sql").read_text()
USER_A_ID = UUID("10000000-0000-4000-8000-000000000001")
USER_B_ID = UUID("20000000-0000-4000-8000-000000000002")
APP_ROLE = "finance_app_test"
APP_PASSWORD = "finance_app_test"


def _app_database_url(admin_url: str) -> str:
    settings = conninfo_to_dict(admin_url)
    settings.update(user=APP_ROLE, password=APP_PASSWORD)
    return make_conninfo(**settings)


@pytest.fixture(scope="module")
def postgres_url() -> str:
    admin_url = os.getenv("TEST_DATABASE_URL")
    if not admin_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    database_name = conninfo_to_dict(admin_url).get("dbname", "postgres")
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute("create extension if not exists pgcrypto")
        connection.execute(
            f"""
            do $$
            begin
              if not exists (select 1 from pg_roles where rolname = '{APP_ROLE}') then
                create role {APP_ROLE} login password '{APP_PASSWORD}'
                  nosuperuser nobypassrls;
              end if;
            end
            $$
            """,
        )
        connection.execute(
            sql.SQL("grant connect, create on database {} to {}").format(
                sql.Identifier(database_name),
                sql.Identifier(APP_ROLE),
            ),
        )
        connection.execute(f"grant create, usage on schema public to {APP_ROLE}")
        connection.execute("drop table if exists transactions, accounts, categories cascade")
        connection.execute("drop function if exists enforce_transaction_reference_ownership()")
        connection.execute("drop schema if exists auth cascade")

    app_url = _app_database_url(admin_url)
    with psycopg.connect(app_url, autocommit=True) as connection:
        connection.execute(INIT_SQL)
        connection.execute(
            "insert into auth.users (id) values (%s), (%s)",
            (USER_A_ID, USER_B_ID),
        )

    return app_url


def test_postgres_rls_and_transaction_references(postgres_url: str) -> None:
    categories = PostgresCategoryRepository(postgres_url)
    accounts = PostgresAccountRepository(postgres_url)
    transactions = PostgresTransactionRepository(postgres_url)

    user_a_category = categories.create(
        USER_A_ID,
        CategoryCreate(name="Freelance", color="#123ABC"),
    )
    user_b_category = categories.create(
        USER_B_ID,
        CategoryCreate(name="Private", color="#ABC123"),
    )
    user_a_account = accounts.create(USER_A_ID, AccountCreate(name="Checking"))
    user_b_account = accounts.create(USER_B_ID, AccountCreate(name="Secret"))

    assert len([item for item in categories.list(USER_A_ID) if item.user_id is None]) == 10
    assert categories.get(USER_A_ID, user_b_category.id) is None
    assert accounts.get(USER_A_ID, user_b_account.id) is None

    transaction = transactions.create(
        USER_A_ID,
        TransactionCreate(
            amount=Decimal("25.00"),
            type=TxType.expense,
            description="Supplies",
            date=date(2026, 7, 20),
            category_id=user_a_category.id,
            account_id=user_a_account.id,
        ),
    )
    assert transactions.get(USER_B_ID, transaction.id) is None

    with pytest.raises(InvalidReferenceError) as category_error:
        transactions.create(
            USER_A_ID,
            TransactionCreate(
                amount=Decimal("1.00"),
                type=TxType.expense,
                date=date(2026, 7, 20),
                category_id=user_b_category.id,
            ),
        )
    assert category_error.value.field == "category_id"

    with pytest.raises(InvalidReferenceError) as account_error:
        transactions.create(
            USER_A_ID,
            TransactionCreate(
                amount=Decimal("1.00"),
                type=TxType.expense,
                date=date(2026, 7, 20),
                account_id=user_b_account.id,
            ),
        )
    assert account_error.value.field == "account_id"

    with (
        pytest.raises(psycopg.errors.InsufficientPrivilege),
        database_session(postgres_url, USER_A_ID) as connection,
    ):
        connection.execute(
            "insert into accounts (user_id, name) values (%s, 'Impersonated')",
            (USER_B_ID,),
        )

    assert categories.delete(USER_A_ID, user_a_category.id)
    assert accounts.delete(USER_A_ID, user_a_account.id)
    preserved = transactions.get(USER_A_ID, transaction.id)
    assert preserved is not None
    assert preserved.category_id is None
    assert preserved.account_id is None


def test_dashboard_aggregates_only_the_current_users_transactions(postgres_url: str) -> None:
    categories = PostgresCategoryRepository(postgres_url)
    transactions = PostgresTransactionRepository(postgres_url)
    dashboard = PostgresDashboardRepository(postgres_url)
    user_a_category = categories.create(
        USER_A_ID,
        CategoryCreate(name="Business", color="#123ABC"),
    )

    for user_id, payload in (
        (
            USER_A_ID,
            TransactionCreate(
                amount=Decimal("1000.00"),
                type=TxType.income,
                date=date(2026, 7, 1),
            ),
        ),
        (
            USER_A_ID,
            TransactionCreate(
                amount=Decimal("30.00"),
                type=TxType.expense,
                date=date(2026, 7, 2),
                category_id=user_a_category.id,
            ),
        ),
        (
            USER_A_ID,
            TransactionCreate(
                amount=Decimal("20.00"),
                type=TxType.expense,
                date=date(2026, 7, 8),
            ),
        ),
        (
            USER_A_ID,
            TransactionCreate(
                amount=Decimal("777.00"),
                type=TxType.income,
                date=date(2026, 6, 30),
            ),
        ),
        (
            USER_A_ID,
            TransactionCreate(
                amount=Decimal("10.00"),
                type=TxType.expense,
                date=date(2026, 7, 10),
            ),
        ),
        (
            USER_B_ID,
            TransactionCreate(
                amount=Decimal("999.00"),
                type=TxType.expense,
                date=date(2026, 7, 2),
            ),
        ),
    ):
        transactions.create(user_id, payload)

    result = dashboard.get(
        USER_A_ID,
        date(2026, 7, 1),
        date(2026, 7, 10),
        DashboardBucket.daily,
    )

    assert result.income == Decimal("1000.00")
    assert result.expense == Decimal("60.00")
    assert [
        (item.category_id, item.name, item.color, item.amount, item.percentage)
        for item in result.categories
    ] == [
        (user_a_category.id, "Business", "#123ABC", Decimal("30.00"), Decimal("50.00")),
        (None, "Uncategorized", "#6B7280", Decimal("30.00"), Decimal("50.00")),
    ]
    assert [
        (item.period_start, item.income, item.expense)
        for item in result.trend
    ] == [
        (date(2026, 7, 1), Decimal("1000.00"), Decimal("0.00")),
        (date(2026, 7, 2), Decimal("0.00"), Decimal("30.00")),
        (date(2026, 7, 8), Decimal("0.00"), Decimal("20.00")),
        (date(2026, 7, 10), Decimal("0.00"), Decimal("10.00")),
    ]


def test_dashboard_groups_weekly_and_monthly_trends(postgres_url: str) -> None:
    transactions = PostgresTransactionRepository(postgres_url)
    dashboard = PostgresDashboardRepository(postgres_url)
    for payload in (
        TransactionCreate(
            amount=Decimal("10.00"),
            type=TxType.income,
            date=date(2026, 9, 1),
        ),
        TransactionCreate(
            amount=Decimal("3.00"),
            type=TxType.expense,
            date=date(2026, 9, 6),
        ),
        TransactionCreate(
            amount=Decimal("7.00"),
            type=TxType.income,
            date=date(2026, 9, 7),
        ),
        TransactionCreate(
            amount=Decimal("5.00"),
            type=TxType.expense,
            date=date(2026, 10, 1),
        ),
    ):
        transactions.create(USER_A_ID, payload)

    weekly = dashboard.get(
        USER_A_ID,
        date(2026, 9, 1),
        date(2026, 10, 1),
        DashboardBucket.weekly,
    )
    monthly = dashboard.get(
        USER_A_ID,
        date(2026, 9, 1),
        date(2026, 10, 1),
        DashboardBucket.monthly,
    )

    assert [(item.period_start, item.income, item.expense) for item in weekly.trend] == [
        (date(2026, 8, 31), Decimal("10.00"), Decimal("3.00")),
        (date(2026, 9, 7), Decimal("7.00"), Decimal("0.00")),
        (date(2026, 9, 28), Decimal("0.00"), Decimal("5.00")),
    ]
    assert [(item.period_start, item.income, item.expense) for item in monthly.trend] == [
        (date(2026, 9, 1), Decimal("17.00"), Decimal("3.00")),
        (date(2026, 10, 1), Decimal("0.00"), Decimal("5.00")),
    ]


def test_dashboard_index_is_valid_non_partial_and_orders_user_before_date(postgres_url: str) -> None:
    with psycopg.connect(postgres_url, autocommit=True, row_factory=dict_row) as connection:
        connection.execute(MIGRATION_SQL)
        connection.execute(MIGRATION_SQL)
        definition = connection.execute(
            """
            select
              table_schema.nspname as schema_name,
              table_class.relname as table_name,
              index_data.indisvalid as is_valid,
              index_data.indpred is null as is_not_partial,
              array(
                select attribute.attname
                from unnest(index_data.indkey) with ordinality as key_column(attnum, position)
                join pg_attribute attribute
                  on attribute.attrelid = index_data.indrelid
                 and attribute.attnum = key_column.attnum
                order by key_column.position
              ) as columns
            from pg_index index_data
            join pg_class table_class on table_class.oid = index_data.indrelid
            join pg_namespace table_schema on table_schema.oid = table_class.relnamespace
            where index_data.indexrelid = 'public.transactions_user_date_idx'::regclass
            """
        ).fetchone()

    assert definition == {
        "schema_name": "public",
        "table_name": "transactions",
        "is_valid": True,
        "is_not_partial": True,
        "columns": ["user_id", "date"],
    }


def test_dashboard_keeps_large_aggregate_totals_as_numeric(postgres_url: str) -> None:
    transactions = PostgresTransactionRepository(postgres_url)
    dashboard = PostgresDashboardRepository(postgres_url)
    for _ in range(2):
        transactions.create(
            USER_A_ID,
            TransactionCreate(
                amount=Decimal("9999999999.99"),
                type=TxType.income,
                date=date(2026, 8, 1),
            ),
        )

    result = dashboard.get(
        USER_A_ID,
        date(2026, 8, 1),
        date(2026, 8, 1),
        DashboardBucket.daily,
    )

    assert result.income == Decimal("19999999999.98")


def test_dashboard_omits_zero_total_expense_categories(postgres_url: str) -> None:
    dashboard = PostgresDashboardRepository(postgres_url)
    with database_session(postgres_url, USER_A_ID) as connection:
        connection.execute(
            "insert into transactions (user_id, amount, type, date) values (%s, 0.00, 'expense', %s)",
            (USER_A_ID, date(2026, 8, 2)),
        )

    result = dashboard.get(
        USER_A_ID,
        date(2026, 8, 2),
        date(2026, 8, 2),
        DashboardBucket.daily,
    )

    assert result.expense == Decimal("0.00")
    assert result.categories == []


@pytest.mark.parametrize(
    ("bucket", "bucket_sql"),
    [
        (DashboardBucket.daily, "t.date"),
        (DashboardBucket.weekly, "date_trunc('week', t.date)::date"),
        (DashboardBucket.monthly, "date_trunc('month', t.date)::date"),
    ],
)
def test_dashboard_emits_tenant_date_predicates_and_trusted_bucket_expression(
    monkeypatch: pytest.MonkeyPatch,
    bucket: DashboardBucket,
    bucket_sql: str,
) -> None:
    class QueryCaptureConnection:
        def __init__(self) -> None:
            self.queries: list[tuple[str, tuple[date, date]]] = []

        def execute(self, query: str, params: tuple[date, date]) -> QueryCaptureConnection:
            self.queries.append((query, params))
            return self

        def fetchone(self) -> dict[str, Decimal]:
            return {"income": Decimal("1.00"), "expense": Decimal("0.00")}

        def fetchall(self) -> list[dict[str, Decimal]]:
            return []

    connection = QueryCaptureConnection()

    @contextmanager
    def capture_session(
        _database_url: str,
        _user_id: UUID,
        *,
        repeatable_read: bool = False,
    ):
        assert repeatable_read is True
        yield connection

    monkeypatch.setattr("app.repositories.dashboard.database_session", capture_session)
    date_from = date(2026, 1, 2)
    date_to = date(2026, 3, 4)

    result = PostgresDashboardRepository("postgresql://query-capture").get(
        USER_A_ID,
        date_from,
        date_to,
        bucket,
    )

    assert result.income == Decimal("1.00")
    assert len(connection.queries) == 3
    for query, params in connection.queries:
        assert "t.user_id = current_setting('app.user_id')::uuid" in query
        assert "t.date between %s and %s" in query
        assert params == (date_from, date_to)
    assert f"{bucket_sql} as period_start" in connection.queries[2][0]
    assert f"group by {bucket_sql}" in connection.queries[2][0]


def test_dashboard_starts_a_repeatable_read_snapshot_before_aggregation_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class QueryCaptureConnection:
        def __init__(self) -> None:
            self.queries: list[str] = []

        def execute(
            self,
            query: str,
            _params: tuple[date, date] | None = None,
        ) -> QueryCaptureConnection:
            self.queries.append(query)
            return self

        def fetchone(self) -> dict[str, Decimal]:
            return {"income": Decimal("0.00"), "expense": Decimal("0.00")}

        def fetchall(self) -> list[dict[str, Decimal]]:
            return []

    connection = QueryCaptureConnection()

    snapshot_requested = False

    @contextmanager
    def capture_session(
        _database_url: str,
        _user_id: UUID,
        *,
        repeatable_read: bool = False,
    ):
        nonlocal snapshot_requested
        snapshot_requested = repeatable_read
        yield connection

    monkeypatch.setattr("app.repositories.dashboard.database_session", capture_session)

    PostgresDashboardRepository("postgresql://query-capture").get(
        USER_A_ID,
        date(2026, 1, 1),
        date(2026, 1, 31),
        DashboardBucket.daily,
    )

    assert snapshot_requested is True
    assert len(connection.queries) == 3
    assert all("from transactions t" in query for query in connection.queries)


def test_database_session_sets_repeatable_read_before_the_rls_user_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Transaction:
        def __enter__(self) -> None:
            return None

        def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
            return None

    class Connection:
        def __init__(self) -> None:
            self.queries: list[tuple[str, tuple[str, ...]]] = []

        def __enter__(self) -> Self:
            return self

        def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
            return None

        def transaction(self) -> Transaction:
            return Transaction()

        def execute(self, query: str, params: tuple[str, ...] = ()) -> None:
            self.queries.append((query, params))

    connection = Connection()
    monkeypatch.setattr("app.repositories.base.psycopg.connect", lambda *_args, **_kwargs: connection)

    with database_session(
        "postgresql://query-capture",
        USER_A_ID,
        repeatable_read=True,
    ):
        pass

    assert connection.queries == [
        ("set transaction isolation level repeatable read", ()),
        ("select set_config('app.user_id', %s, true)", (str(USER_A_ID),)),
    ]


def test_dashboard_postgres_category_order_breaks_equal_name_and_amount_ties_by_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class QueryCaptureConnection:
        def __init__(self) -> None:
            self.queries: list[str] = []

        def execute(
            self,
            query: str,
            _params: tuple[date, date] | None = None,
        ) -> QueryCaptureConnection:
            self.queries.append(query)
            return self

        def fetchone(self) -> dict[str, Decimal]:
            return {"income": Decimal("0.00"), "expense": Decimal("0.00")}

        def fetchall(self) -> list[dict[str, Decimal]]:
            return []

    connection = QueryCaptureConnection()

    @contextmanager
    def capture_session(
        _database_url: str,
        _user_id: UUID,
        *,
        repeatable_read: bool = False,
    ):
        assert repeatable_read is True
        yield connection

    monkeypatch.setattr("app.repositories.dashboard.database_session", capture_session)

    PostgresDashboardRepository("postgresql://query-capture").get(
        USER_A_ID,
        date(2026, 1, 1),
        date(2026, 1, 31),
        DashboardBucket.daily,
    )

    categories_query = next(
        query for query in connection.queries if "expense_totals as" in query
    )
    assert "order by expense_totals.amount desc, lower(name), category_id" in categories_query


def test_dashboard_repository_builder_uses_configured_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://dashboard-test")
    from app.repositories import build_dashboard_repository

    assert isinstance(build_dashboard_repository(), PostgresDashboardRepository)
