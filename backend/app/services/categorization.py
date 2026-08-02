from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.repositories.categorization_rules import CategorizationRuleRecord
from app.schemas import TxType


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
