from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.repositories.accounts import PostgresAccountRepository
from app.repositories.base import InvalidReferenceError, database_session
from app.repositories.categories import PostgresCategoryRepository
from app.repositories.transactions import PostgresTransactionRepository
from app.schemas import AccountCreate, CategoryCreate, TransactionCreate, TxType


ROOT = Path(__file__).parents[2]
INIT_SQL = (ROOT / "backend/sql/init.sql").read_text()
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

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with database_session(postgres_url, USER_A_ID) as connection:
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
