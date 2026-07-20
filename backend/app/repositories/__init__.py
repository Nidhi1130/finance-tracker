from __future__ import annotations

from os import getenv

from app.repositories.accounts import (
    AccountRepository,
    InMemoryAccountRepository,
    PostgresAccountRepository,
)
from app.repositories.base import DuplicateResourceError, ForbiddenResourceError
from app.repositories.categories import (
    CategoryRepository,
    InMemoryCategoryRepository,
    PostgresCategoryRepository,
)
from app.repositories.transactions import (
    InMemoryTransactionRepository,
    PostgresTransactionRepository,
    TransactionRepository,
)


def build_category_repository() -> CategoryRepository:
    database_url = getenv("DATABASE_URL")
    if database_url:
        return PostgresCategoryRepository(database_url)
    return InMemoryCategoryRepository()


def build_account_repository() -> AccountRepository:
    database_url = getenv("DATABASE_URL")
    if database_url:
        return PostgresAccountRepository(database_url)
    return InMemoryAccountRepository()


def build_transaction_repository() -> TransactionRepository:
    database_url = getenv("DATABASE_URL")
    if database_url:
        return PostgresTransactionRepository(database_url)
    return InMemoryTransactionRepository()


category_repository = build_category_repository()
account_repository = build_account_repository()
transaction_repository = build_transaction_repository()


__all__ = [
    "DuplicateResourceError",
    "ForbiddenResourceError",
    "account_repository",
    "build_account_repository",
    "build_category_repository",
    "build_transaction_repository",
    "category_repository",
    "transaction_repository",
]
