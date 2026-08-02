from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.repositories.categorization_rules import CategorizationRuleRecord
from app.services.categorization import match_rule


RULE_A = UUID("10000000-0000-4000-8000-000000000001")
RULE_B = UUID("10000000-0000-4000-8000-000000000002")
USER_ID = UUID("20000000-0000-4000-8000-000000000001")
CATEGORY_ID = UUID("30000000-0000-4000-8000-000000000001")


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
