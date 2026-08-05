from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from app import schemas

ROOT = Path(__file__).parents[2]
INIT_SQL = (ROOT / "backend/sql/init.sql").read_text()
MIGRATION_SQL = (
    ROOT / "backend/sql/migrations/002_phase_2_categories_accounts.sql"
).read_text()
PHASE4_MIGRATION = ROOT / "backend/sql/migrations/004_phase_4_smart_categorization.sql"

DEFAULT_NAMES = {
    "Housing",
    "Groceries",
    "Dining",
    "Transport",
    "Utilities",
    "Health",
    "Entertainment",
    "Shopping",
    "Salary",
    "Other",
}


def test_phase2_sql_forces_rls_and_nulls_deleted_references() -> None:
    combined = f"{INIT_SQL}\n{MIGRATION_SQL}".lower()
    assert "force row level security" in combined
    assert combined.count("on delete set null") >= 4
    assert "transactions_reference_ownership" in combined
    assert "enforce_transaction_reference_ownership" in combined


def test_phase2_sql_seeds_every_approved_global_category() -> None:
    for name in DEFAULT_NAMES:
        assert f"'{name}'" in INIT_SQL
        assert f"'{name}'" in MIGRATION_SQL
    for suffix in range(1, 11):
        stable_id = f"00000000-0000-4000-8000-{suffix:012d}"
        assert stable_id in INIT_SQL
        assert stable_id in MIGRATION_SQL


def test_phase4_migration_defines_rules_rls_and_transaction_metadata() -> None:
    assert PHASE4_MIGRATION.exists()
    sql = PHASE4_MIGRATION.read_text()
    assert "create table if not exists categorization_rules" in sql.lower()
    assert "alter table categorization_rules force row level security" in sql.lower()
    assert "category_source" in sql
    assert "categorization_status" in sql
    assert "on delete cascade" in sql.lower()


def test_phase4_schema_serializes_categorization_enums_and_normalizes_keywords() -> None:
    assert hasattr(schemas, "CategorizationSource")
    assert hasattr(schemas, "CategorizationStatus")
    assert hasattr(schemas, "CategorizationRuleCreate")
    assert hasattr(schemas, "CategorizationRuleUpdate")
    assert hasattr(schemas, "CategorizationRuleOut")
    assert hasattr(schemas, "CategorizationRuleListResponse")

    category_id = UUID("30000000-0000-4000-8000-000000000001")
    rule = schemas.CategorizationRuleCreate(
        keyword="  coffee   shop  ",
        category_id=category_id,
    )
    transaction = schemas.TransactionOut(
        id=UUID("40000000-0000-4000-8000-000000000001"),
        amount=Decimal("4.50"),
        type=schemas.TxType.expense,
        description="Coffee",
        date="2026-08-02",
        category_id=category_id,
        account_id=None,
        category_source=schemas.CategorizationSource.rule,
        categorization_status=schemas.CategorizationStatus.categorized,
        categorized_at=datetime(2026, 8, 2, 12, tzinfo=UTC),
        created_at=datetime(2026, 8, 2, 12, tzinfo=UTC),
        updated_at=datetime(2026, 8, 2, 12, tzinfo=UTC),
    )

    assert rule.keyword == "coffee shop"
    assert transaction.model_dump(mode="json") == {
        "id": "40000000-0000-4000-8000-000000000001",
        "amount": "4.50",
        "type": "expense",
        "description": "Coffee",
        "date": "2026-08-02",
        "category_id": "30000000-0000-4000-8000-000000000001",
        "account_id": None,
        "category_source": "rule",
        "categorization_status": "categorized",
        "categorized_at": "2026-08-02T12:00:00Z",
        "created_at": "2026-08-02T12:00:00Z",
        "updated_at": "2026-08-02T12:00:00Z",
    }

    with pytest.raises(ValueError, match="keyword must contain between 1 and 120 characters"):
        schemas.CategorizationRuleCreate(keyword="   ", category_id=category_id)
    with pytest.raises(ValueError, match="keyword must contain between 1 and 120 characters"):
        schemas.CategorizationRuleCreate(keyword="a" * 121, category_id=category_id)
