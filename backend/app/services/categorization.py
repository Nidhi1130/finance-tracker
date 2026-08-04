from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.repositories.base import InvalidReferenceError
from app.repositories.categories import CategoryRepository
from app.repositories.categorization_rules import (
    CategorizationRuleRecord,
    CategorizationRuleRepository,
)
from app.repositories.transactions import TransactionRepository
from app.schemas import CategorizationSource, CategorizationStatus, TxType


@dataclass(frozen=True)
class CategoryCandidate:
    id: UUID
    name: str


class CategorizationProvider(Protocol):
    def categorize(
        self,
        *,
        description: str,
        tx_type: TxType,
        categories: Sequence[CategoryCandidate],
    ) -> UUID | None: ...


@dataclass
class CategorizationService:
    transaction_repository: TransactionRepository
    rule_repository: CategorizationRuleRepository
    category_repository: CategoryRepository
    provider: CategorizationProvider | None = None

    def categorize(self, user_id: UUID, transaction_id: UUID) -> None:
        transaction = self.transaction_repository.get(user_id, transaction_id)
        if (
            transaction is None
            or transaction.category_id is not None
            or transaction.categorization_status is not CategorizationStatus.pending
        ):
            return

        if not transaction.description or not transaction.description.strip():
            self.transaction_repository.finish_without_category(
                user_id,
                transaction_id,
                CategorizationStatus.not_requested,
            )
            return

        matched_rule = match_rule(
            transaction.description,
            self.rule_repository.list(user_id, enabled_only=True),
        )
        if matched_rule is not None:
            self._apply_category(
                user_id,
                transaction_id,
                matched_rule.category_id,
                CategorizationSource.rule,
            )
            return

        if self.provider is None:
            self.transaction_repository.finish_without_category(
                user_id,
                transaction_id,
                CategorizationStatus.not_requested,
            )
            return

        categories = [
            CategoryCandidate(id=category.id, name=category.name)
            for category in self.category_repository.list(user_id)
        ]
        try:
            category_id = self.provider.categorize(
                description=transaction.description,
                tx_type=transaction.type,
                categories=categories,
            )
        except Exception:  # noqa: BLE001 - background task must never crash on provider errors
            self.transaction_repository.finish_without_category(
                user_id,
                transaction_id,
                CategorizationStatus.failed,
            )
            return

        if category_id is None:
            self.transaction_repository.finish_without_category(
                user_id,
                transaction_id,
                CategorizationStatus.not_requested,
            )
            return
        self._apply_category(
            user_id,
            transaction_id,
            category_id,
            CategorizationSource.openai,
        )

    def _apply_category(
        self,
        user_id: UUID,
        transaction_id: UUID,
        category_id: UUID,
        source: CategorizationSource,
    ) -> None:
        try:
            applied = self.transaction_repository.apply_automatic_category(
                user_id,
                transaction_id,
                category_id,
                source,
            )
        except InvalidReferenceError:
            applied = None
        if applied is None:
            self.transaction_repository.finish_without_category(
                user_id,
                transaction_id,
                CategorizationStatus.failed,
            )


def match_rule(
    description: str | None,
    rules: Sequence[CategorizationRuleRecord],
) -> CategorizationRuleRecord | None:
    if not description or not description.strip():
        return None
    folded = description.casefold()
    matches = [
        rule
        for rule in rules
        if rule.enabled and rule.keyword.casefold() in folded
    ]
    return min(
        matches,
        key=lambda rule: (-len(rule.keyword), rule.keyword.casefold(), str(rule.id)),
        default=None,
    )
