from pathlib import Path


ROOT = Path(__file__).parents[2]
INIT_SQL = (ROOT / "backend/sql/init.sql").read_text()
MIGRATION_SQL = (
    ROOT / "backend/sql/migrations/002_phase_2_categories_accounts.sql"
).read_text()

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
