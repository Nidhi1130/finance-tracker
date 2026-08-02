from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from datetime import datetime, timezone
from decimal import Decimal
from threading import Event, Thread
from typing import Callable
from uuid import UUID

from app.repositories.categories import InMemoryCategoryRepository
from app.repositories.categorization_rules import InMemoryCategorizationRuleRepository
from app.repositories.categorization_rules import CategorizationRuleRecord
from app.repositories.transactions import InMemoryTransactionRepository, TransactionRecord
from app.schemas import (
    CategorizationRuleCreate,
    CategorizationSource,
    CategorizationStatus,
    CategoryCreate,
    TransactionCreate,
    TransactionUpdate,
    TxType,
)
from app.services import categorization as categorization_module
from app.services.categorization import CategoryCandidate, match_rule


RULE_A = UUID("10000000-0000-4000-8000-000000000001")
RULE_B = UUID("10000000-0000-4000-8000-000000000002")
USER_ID = UUID("20000000-0000-4000-8000-000000000001")
CATEGORY_ID = UUID("30000000-0000-4000-8000-000000000001")


@dataclass
class FakeProvider:
    result: UUID | None = None
    error: Exception | None = None
    before_return: Callable[[], None] | None = None
    calls: list[tuple[str, TxType, list[CategoryCandidate]]] = field(default_factory=list)

    def categorize(
        self,
        *,
        description: str,
        tx_type: TxType,
        categories: list[CategoryCandidate],
    ) -> UUID | None:
        self.calls.append((description, tx_type, list(categories)))
        if self.before_return is not None:
            self.before_return()
        if self.error is not None:
            raise self.error
        return self.result


@dataclass
class BlockingCategoryRepository(InMemoryCategoryRepository):
    blocked_category_id: UUID | None = None
    validation_entered: Event = field(default_factory=Event)
    release_validation: Event = field(default_factory=Event)

    def is_accessible(self, user_id: UUID, category_id: UUID) -> bool:
        accessible = super().is_accessible(user_id, category_id)
        if category_id == self.blocked_category_id:
            self.validation_entered.set()
            if not self.release_validation.wait(timeout=2):
                raise TimeoutError("automatic category validation was not released")
        return accessible


class PausingStatusReadTransactionRecord(TransactionRecord):
    def pause_next_status_read(self, entered: Event, release: Event) -> None:
        self._status_read_entered = entered
        self._release_status_read = release
        self._pause_status_read = True

    def __getattribute__(self, name: str):
        value = super().__getattribute__(name)
        if name == "categorization_status" and getattr(self, "_pause_status_read", False):
            self._pause_status_read = False
            self._status_read_entered.set()
            if not self._release_status_read.wait(timeout=2):
                raise TimeoutError("status read was not released")
        return value


def categorization_context(provider: FakeProvider | None):
    categories = InMemoryCategoryRepository()
    transactions = InMemoryTransactionRepository(category_repository=categories)
    rules = InMemoryCategorizationRuleRepository(category_repository=categories)
    dining = categories.create(USER_ID, CategoryCreate(name="Dining out", color="#EA580C"))
    shopping = categories.create(USER_ID, CategoryCreate(name="Shopping trip", color="#CA8A04"))
    service = categorization_module.CategorizationService(
        transaction_repository=transactions,
        rule_repository=rules,
        category_repository=categories,
        provider=provider,
    )
    return service, transactions, rules, dining, shopping


def pending_transaction(
    transactions: InMemoryTransactionRepository,
    description: str | None = "UBER EATS STOCKHOLM",
):
    return transactions.create(
        USER_ID,
        TransactionCreate(
            amount=Decimal("18.25"),
            type=TxType.expense,
            description=description,
            date=date(2026, 8, 2),
        ),
    )


def rule(keyword: str, rule_id: UUID, *, enabled: bool = True) -> CategorizationRuleRecord:
    timestamp = datetime(2026, 8, 2, tzinfo=timezone.utc)
    return CategorizationRuleRecord(
        id=rule_id,
        user_id=USER_ID,
        keyword=keyword,
        category_id=CATEGORY_ID,
        category_name="Dining",
        category_color="#EA580C",
        enabled=enabled,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_match_rule_matches_case_insensitive_substrings() -> None:
    matched = match_rule("Monthly SPOTIFY premium", [rule("spotify", RULE_A)])

    assert matched is not None
    assert matched.id == RULE_A


def test_match_rule_prefers_longest_keyword() -> None:
    rules = [rule("uber", RULE_A), rule("uber eats", RULE_B)]

    matched = match_rule("UBER EATS STOCKHOLM", rules)

    assert matched is not None
    assert matched.id == RULE_B


def test_match_rule_excludes_disabled_rules() -> None:
    matched = match_rule("NETFLIX.COM", [rule("netflix", RULE_A, enabled=False)])

    assert matched is None


def test_match_rule_breaks_equal_length_ties_by_keyword_then_id() -> None:
    by_keyword = rule("cafe", RULE_B)
    by_id = rule("cafe", RULE_A)
    rules = [by_keyword, by_id, rule("café", RULE_B)]

    assert match_rule("Cafe and café", rules) == by_id
    assert match_rule("Cafe and café", list(reversed(rules))) == by_id


def test_match_rule_returns_none_without_a_description_or_match() -> None:
    rules = [rule("spotify", RULE_A)]

    assert match_rule(None, rules) is None
    assert match_rule("   ", rules) is None
    assert match_rule("City library", rules) is None


def test_rule_match_assigns_rule_source_without_calling_provider() -> None:
    provider = FakeProvider(result=CATEGORY_ID)
    service, transactions, rules, dining, _ = categorization_context(provider)
    rules.create(
        USER_ID,
        CategorizationRuleCreate(keyword="uber eats", category_id=dining.id),
    )
    transaction = pending_transaction(transactions)

    service.categorize(USER_ID, transaction.id)

    categorized = transactions.get(USER_ID, transaction.id)
    assert categorized is not None
    assert categorized.category_id == dining.id
    assert categorized.category_source is CategorizationSource.rule
    assert categorized.categorization_status is CategorizationStatus.categorized
    assert categorized.categorized_at is not None
    assert provider.calls == []


def test_openai_fallback_assigns_openai_source() -> None:
    provider = FakeProvider()
    service, transactions, _, _, shopping = categorization_context(provider)
    provider.result = shopping.id
    transaction = pending_transaction(transactions, "Department store")

    service.categorize(USER_ID, transaction.id)

    categorized = transactions.get(USER_ID, transaction.id)
    assert categorized is not None
    assert categorized.category_id == shopping.id
    assert categorized.category_source is CategorizationSource.openai
    assert categorized.categorization_status is CategorizationStatus.categorized
    assert categorized.categorized_at is not None
    assert provider.calls[0][0:2] == ("Department store", TxType.expense)
    assert shopping.id in {candidate.id for candidate in provider.calls[0][2]}


def test_manual_update_wins_over_late_background_result() -> None:
    provider = FakeProvider()
    service, transactions, _, dining, shopping = categorization_context(provider)
    provider.result = shopping.id
    transaction = pending_transaction(transactions, "Department store")
    provider.before_return = lambda: transactions.update(
        USER_ID,
        transaction.id,
        TransactionUpdate(category_id=dining.id),
    )

    service.categorize(USER_ID, transaction.id)

    preserved = transactions.get(USER_ID, transaction.id)
    assert preserved is not None
    assert preserved.category_id == dining.id
    assert preserved.category_source is CategorizationSource.manual
    assert preserved.categorization_status is CategorizationStatus.categorized


def test_provider_failure_marks_failed_without_changing_category() -> None:
    provider = FakeProvider(error=RuntimeError("provider unavailable"))
    service, transactions, _, _, _ = categorization_context(provider)
    transaction = pending_transaction(transactions, "Unknown merchant")

    service.categorize(USER_ID, transaction.id)

    failed = transactions.get(USER_ID, transaction.id)
    assert failed is not None
    assert failed.category_id is None
    assert failed.category_source is None
    assert failed.categorization_status is CategorizationStatus.failed
    assert failed.categorized_at is None


def test_category_deleted_before_provider_result_marks_failed() -> None:
    provider = FakeProvider()
    service, transactions, _, _, shopping = categorization_context(provider)
    provider.result = shopping.id
    transaction = pending_transaction(transactions, "Department store")
    provider.before_return = lambda: service.category_repository.delete(USER_ID, shopping.id)

    service.categorize(USER_ID, transaction.id)

    failed = transactions.get(USER_ID, transaction.id)
    assert failed is not None
    assert failed.category_id is None
    assert failed.category_source is None
    assert failed.categorization_status is CategorizationStatus.failed
    assert failed.categorized_at is None


def test_no_description_or_provider_result_finishes_not_requested() -> None:
    provider = FakeProvider(result=None)
    service, transactions, _, _, _ = categorization_context(provider)
    no_description = pending_transaction(transactions, None)
    no_result = pending_transaction(transactions, "Unknown merchant")

    service.categorize(USER_ID, no_description.id)
    service.categorize(USER_ID, no_result.id)

    assert transactions.get(USER_ID, no_description.id).categorization_status is (
        CategorizationStatus.not_requested
    )
    assert transactions.get(USER_ID, no_result.id).categorization_status is (
        CategorizationStatus.not_requested
    )
    assert len(provider.calls) == 1


def test_missing_provider_marks_failed_without_changing_category() -> None:
    service, transactions, _, _, _ = categorization_context(None)
    transaction = pending_transaction(transactions, "Unknown merchant")

    service.categorize(USER_ID, transaction.id)

    failed = transactions.get(USER_ID, transaction.id)
    assert failed is not None
    assert failed.category_id is None
    assert failed.categorization_status is CategorizationStatus.failed


def test_in_memory_automatic_apply_is_atomic_with_manual_update() -> None:
    categories = BlockingCategoryRepository()
    transactions = InMemoryTransactionRepository(category_repository=categories)
    automatic_category = categories.create(
        USER_ID,
        CategoryCreate(name="Automatic", color="#CA8A04"),
    )
    manual_category = categories.create(
        USER_ID,
        CategoryCreate(name="Manual", color="#EA580C"),
    )
    transaction = pending_transaction(transactions, "Concurrent merchant")
    categories.blocked_category_id = automatic_category.id
    errors: list[BaseException] = []

    def apply_automatic() -> None:
        try:
            transactions.apply_automatic_category(
                USER_ID,
                transaction.id,
                automatic_category.id,
                CategorizationSource.openai,
            )
        except BaseException as error:
            errors.append(error)

    automatic_thread = Thread(target=apply_automatic)
    automatic_thread.start()
    assert categories.validation_entered.wait(timeout=1)

    manual_started = Event()
    manual_done = Event()

    def apply_manual() -> None:
        manual_started.set()
        try:
            transactions.update(
                USER_ID,
                transaction.id,
                TransactionUpdate(category_id=manual_category.id),
            )
        except BaseException as error:
            errors.append(error)
        finally:
            manual_done.set()

    manual_thread = Thread(target=apply_manual)
    manual_thread.start()
    assert manual_started.wait(timeout=1)
    manual_completed_before_release = manual_done.wait(timeout=0.2)
    categories.release_validation.set()
    automatic_thread.join(timeout=1)
    manual_thread.join(timeout=1)

    assert not automatic_thread.is_alive()
    assert not manual_thread.is_alive()
    assert not manual_completed_before_release
    assert errors == []
    preserved = transactions.get(USER_ID, transaction.id)
    assert preserved is not None
    assert preserved.category_id == manual_category.id
    assert preserved.category_source is CategorizationSource.manual
    assert preserved.categorization_status is CategorizationStatus.categorized


def test_in_memory_finish_is_atomic_with_manual_update() -> None:
    categories = InMemoryCategoryRepository()
    transactions = InMemoryTransactionRepository(category_repository=categories)
    manual_category = categories.create(
        USER_ID,
        CategoryCreate(name="Manual after failure", color="#EA580C"),
    )
    created = pending_transaction(transactions, "Concurrent merchant")
    transaction = PausingStatusReadTransactionRecord(**created.__dict__)
    transactions._items[USER_ID][transaction.id] = transaction
    status_read_entered = Event()
    release_status_read = Event()
    transaction.pause_next_status_read(status_read_entered, release_status_read)
    errors: list[BaseException] = []

    def finish_automatic() -> None:
        try:
            transactions.finish_without_category(
                USER_ID,
                transaction.id,
                CategorizationStatus.failed,
            )
        except BaseException as error:
            errors.append(error)

    finish_thread = Thread(target=finish_automatic)
    finish_thread.start()
    assert status_read_entered.wait(timeout=1)

    manual_started = Event()
    manual_done = Event()

    def apply_manual() -> None:
        manual_started.set()
        try:
            transactions.update(
                USER_ID,
                transaction.id,
                TransactionUpdate(category_id=manual_category.id),
            )
        except BaseException as error:
            errors.append(error)
        finally:
            manual_done.set()

    manual_thread = Thread(target=apply_manual)
    manual_thread.start()
    assert manual_started.wait(timeout=1)
    manual_completed_before_release = manual_done.wait(timeout=0.2)
    release_status_read.set()
    finish_thread.join(timeout=1)
    manual_thread.join(timeout=1)

    assert not finish_thread.is_alive()
    assert not manual_thread.is_alive()
    assert not manual_completed_before_release
    assert errors == []
    preserved = transactions.get(USER_ID, transaction.id)
    assert preserved is not None
    assert preserved.category_id == manual_category.id
    assert preserved.category_source is CategorizationSource.manual
    assert preserved.categorization_status is CategorizationStatus.categorized
