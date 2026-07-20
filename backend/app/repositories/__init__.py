from __future__ import annotations

from os import getenv

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


def build_transaction_repository() -> TransactionRepository:
    database_url = getenv("DATABASE_URL")
    if database_url:
        return PostgresTransactionRepository(database_url)
    return InMemoryTransactionRepository()


category_repository = build_category_repository()
transaction_repository = build_transaction_repository()


__all__ = [
    "DuplicateResourceError",
    "ForbiddenResourceError",
    "build_category_repository",
    "build_transaction_repository",
    "category_repository",
    "transaction_repository",
]
