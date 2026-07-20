from __future__ import annotations

from os import getenv

from app.repositories.accounts import (
    AccountRepository,
    InMemoryAccountRepository,
    PostgresAccountRepository,
)
from app.repositories.base import (
    DuplicateResourceError,
    ForbiddenResourceError,
    InvalidReferenceError,
)
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


def build_transaction_repository(
    categories: CategoryRepository | None = None,
    accounts: AccountRepository | None = None,
) -> TransactionRepository:
    database_url = getenv("DATABASE_URL")
    if database_url:
        return PostgresTransactionRepository(database_url)
    return InMemoryTransactionRepository(
        category_repository=categories,
        account_repository=accounts,
    )


category_repository = build_category_repository()
account_repository = build_account_repository()
transaction_repository = build_transaction_repository(category_repository, account_repository)
if isinstance(transaction_repository, InMemoryTransactionRepository):
    if isinstance(category_repository, InMemoryCategoryRepository):
        category_repository.set_delete_callback(
            transaction_repository.clear_category_reference,
        )
    if isinstance(account_repository, InMemoryAccountRepository):
        account_repository.set_delete_callback(
            transaction_repository.clear_account_reference,
        )


__all__ = [
    "DuplicateResourceError",
    "ForbiddenResourceError",
    "InvalidReferenceError",
    "account_repository",
    "build_account_repository",
    "build_category_repository",
    "build_transaction_repository",
    "category_repository",
    "transaction_repository",
]
