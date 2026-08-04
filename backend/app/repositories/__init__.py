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
from app.repositories.categorization_rules import (
    CategorizationRuleRepository,
    InMemoryCategorizationRuleRepository,
    PostgresCategorizationRuleRepository,
)
from app.repositories.dashboard import (
    DashboardRepository,
    InMemoryDashboardRepository,
    PostgresDashboardRepository,
)
from app.repositories.transactions import (
    InMemoryTransactionRepository,
    PostgresTransactionRepository,
    TransactionRecord,
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


def build_categorization_rule_repository(
    categories: CategoryRepository | None = None,
) -> CategorizationRuleRepository:
    database_url = getenv("DATABASE_URL")
    if database_url:
        return PostgresCategorizationRuleRepository(database_url)
    return InMemoryCategorizationRuleRepository(category_repository=categories)


category_repository = build_category_repository()
account_repository = build_account_repository()
transaction_repository = build_transaction_repository(category_repository, account_repository)
categorization_rule_repository = build_categorization_rule_repository(category_repository)
if isinstance(transaction_repository, InMemoryTransactionRepository):
    if isinstance(category_repository, InMemoryCategoryRepository):
        category_repository.set_delete_callback(
            transaction_repository.clear_category_reference,
        )
    if isinstance(account_repository, InMemoryAccountRepository):
        account_repository.set_delete_callback(
            transaction_repository.clear_account_reference,
        )


def build_dashboard_repository() -> DashboardRepository:
    database_url = getenv("DATABASE_URL")
    if database_url:
        return PostgresDashboardRepository(database_url)
    return InMemoryDashboardRepository(transaction_repository, category_repository)


dashboard_repository = build_dashboard_repository()


__all__ = [
    "DuplicateResourceError",
    "ForbiddenResourceError",
    "InMemoryTransactionRepository",
    "InvalidReferenceError",
    "PostgresTransactionRepository",
    "TransactionRecord",
    "TransactionRepository",
    "account_repository",
    "build_account_repository",
    "build_categorization_rule_repository",
    "build_category_repository",
    "build_dashboard_repository",
    "build_transaction_repository",
    "categorization_rule_repository",
    "category_repository",
    "dashboard_repository",
    "transaction_repository",
]
