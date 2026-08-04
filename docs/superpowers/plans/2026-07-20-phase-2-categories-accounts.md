# Phase 2 Categories and Accounts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver authenticated category/account CRUD, immutable global categories, transaction selectors and filters, RLS isolation, and end-to-end verification.

**Architecture:** Implement vertical slices on `codex/phase-2-categories-accounts`. Postgres enforces ownership and reference integrity, FastAPI exposes thin authenticated resource routes, and Next.js uses a shared authenticated API boundary plus TanStack Query. Each slice is test-first, committed separately, and reviewed before dependent work begins.

**Tech Stack:** PostgreSQL 16, SQL RLS, Python 3.12+, FastAPI, Pydantic, psycopg 3, pytest, Ruff, Next.js 16, React 19, strict TypeScript, TanStack Query, CSS Modules.

## Global Constraints

- The frontend talks only to FastAPI; it never queries Supabase/Postgres directly.
- Every protected route derives `user_id` from the verified Supabase JWT `sub`; no request accepts `user_id`.
- Global categories have `user_id is null`, are readable by every signed-in user, and are immutable to normal users.
- Custom category colors are normalized uppercase `#RRGGBB`; category/account names are trimmed and 1–80 characters.
- Category names are case-insensitively unique per owner; account names are case-insensitively unique per user.
- Transaction category references must be global or current-user-owned; account references must be current-user-owned.
- Deleting a category/account uses `ON DELETE SET NULL` and preserves transactions.
- Use additive migrations; do not rewrite applied migration history. Keep fresh-database bootstrap synchronized.
- Use CSS Modules and existing tokens; do not introduce a component library.
- Update `context/progress-tracker.md` after every meaningful completed slice.

## File Structure

- `backend/sql/migrations/002_phase_2_categories_accounts.sql`: idempotent upgrade for existing databases.
- `backend/sql/init.sql`: synchronized fresh-database schema.
- `backend/app/repositories/`: package containing shared errors/session logic and resource-specific repositories.
- `backend/app/routers/categories.py`, `accounts.py`, `transactions.py`: thin HTTP routes.
- `backend/app/schemas.py`: Pydantic request/output contracts.
- `backend/tests/conftest.py`, `test_categories.py`, `test_accounts.py`, `test_transactions.py`, `test_phase2_postgres.py`: HTTP and Postgres isolation tests.
- `frontend/lib/api.ts`, `categories.ts`, `accounts.ts`: authenticated HTTP boundary and resource contracts.
- `frontend/app/categories/`, `accounts/`: management clients and CSS Modules.
- `frontend/app/transactions/transactions-client.tsx`: named selectors, labels, filters, and query invalidation.

---

### Task 1: Lock the SQL schema, seeds, RLS, and Phase 2 context

**Owner:** Backend/data agent

**Files:**
- Create: `backend/sql/migrations/002_phase_2_categories_accounts.sql`
- Create: `backend/tests/test_phase2_sql.py`
- Create: `context/feature-specs/04-categories-accounts.md`
- Modify: `backend/sql/init.sql`
- Modify: `context/architecture.md`
- Modify: `context/progress-tracker.md`

**Interfaces:**
- Produces the ten stable global-category IDs from the approved design spec.
- Produces `ON DELETE SET NULL` foreign keys and forced RLS required by repository/API tasks.
- Produces SQL function `enforce_transaction_reference_ownership()` and trigger `transactions_reference_ownership`.

- [ ] **Step 1: Write the failing SQL contract test**

Create `backend/tests/test_phase2_sql.py` with tests that read both SQL files and assert:

```python
from pathlib import Path

ROOT = Path(__file__).parents[2]
INIT_SQL = (ROOT / "backend/sql/init.sql").read_text()
MIGRATION_SQL = (
    ROOT / "backend/sql/migrations/002_phase_2_categories_accounts.sql"
).read_text()

DEFAULT_NAMES = {
    "Housing", "Groceries", "Dining", "Transport", "Utilities",
    "Health", "Entertainment", "Shopping", "Salary", "Other",
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
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd backend && ../backend/.venv/bin/pytest tests/test_phase2_sql.py -q` when `.venv` exists, otherwise `/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest tests/test_phase2_sql.py -q`.

Expected: collection/file failure because the migration does not exist, or assertion failures for seeds/forced RLS/delete behavior.

- [ ] **Step 3: Implement the additive migration and synchronize bootstrap**

The migration and matching `init.sql` statements must:

```sql
update categories set color = '#6B7280' where color is null;
alter table categories alter column color set not null;
alter table categories alter column created_at set not null;
alter table accounts alter column created_at set not null;

alter table transactions drop constraint if exists transactions_category_id_fkey;
alter table transactions add constraint transactions_category_id_fkey
  foreign key (category_id) references categories(id) on delete set null;
alter table transactions drop constraint if exists transactions_account_id_fkey;
alter table transactions add constraint transactions_account_id_fkey
  foreign key (account_id) references accounts(id) on delete set null;

create unique index if not exists categories_owner_lower_name_key
  on categories (coalesce(user_id, '00000000-0000-0000-0000-000000000000'::uuid), lower(name));
create unique index if not exists accounts_owner_lower_name_key
  on accounts (user_id, lower(name));
create index if not exists transactions_category_id_idx on transactions(category_id);
create index if not exists transactions_account_id_idx on transactions(account_id);

alter table categories force row level security;
alter table accounts force row level security;
alter table transactions force row level security;
```

Insert these exact rows with `ON CONFLICT (id) DO UPDATE SET name = excluded.name, color = excluded.color, user_id = null`:

```sql
values
  ('00000000-0000-4000-8000-000000000001', null, 'Housing', '#7C3AED'),
  ('00000000-0000-4000-8000-000000000002', null, 'Groceries', '#16A34A'),
  ('00000000-0000-4000-8000-000000000003', null, 'Dining', '#EA580C'),
  ('00000000-0000-4000-8000-000000000004', null, 'Transport', '#2563EB'),
  ('00000000-0000-4000-8000-000000000005', null, 'Utilities', '#0891B2'),
  ('00000000-0000-4000-8000-000000000006', null, 'Health', '#DC2626'),
  ('00000000-0000-4000-8000-000000000007', null, 'Entertainment', '#DB2777'),
  ('00000000-0000-4000-8000-000000000008', null, 'Shopping', '#CA8A04'),
  ('00000000-0000-4000-8000-000000000009', null, 'Salary', '#059669'),
  ('00000000-0000-4000-8000-000000000010', null, 'Other', '#6B7280')
```

Create `enforce_transaction_reference_ownership()` as a `SECURITY DEFINER` trigger function with a fixed `search_path = public, pg_temp`. It raises check-violation SQLSTATE `23514` when `NEW.category_id` is not a global/current-user category or `NEW.account_id` is not current-user-owned. Add a `BEFORE INSERT OR UPDATE OF user_id, category_id, account_id` trigger.

- [ ] **Step 4: Write the project Phase 2 context spec**

`context/feature-specs/04-categories-accounts.md` must copy the locked model, exact defaults, endpoint/status contract, deletion behavior, frontend interactions, and test matrix from `docs/superpowers/specs/2026-07-20-phase-2-categories-accounts-design.md`. Update `architecture.md` with forced RLS, trigger validation, and delete semantics. Update the tracker to `Phase 2 — Categories & Accounts. In progress` and remove the Accounts deferral question.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
cd backend
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest tests/test_phase2_sql.py -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
```

Expected: SQL tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 6: Commit**

```bash
git add backend/sql backend/tests/test_phase2_sql.py context
git commit -m "feat: lock phase 2 data model and rls"
```

---

### Task 2: Build category CRUD with isolation tests

**Owner:** Backend category agent

**Files:**
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/repositories/base.py`
- Create: `backend/app/repositories/categories.py`
- Create: `backend/app/repositories/transactions.py`
- Create: `backend/app/routers/categories.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_categories.py`
- Delete: `backend/app/repositories.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/routers/transactions.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_transactions.py`
- Modify: `context/progress-tracker.md`

**Interfaces:**
- `CategoryCreate(name: str, color: str)` and `CategoryUpdate(name: str, color: str)`.
- `CategoryOut(id: UUID, name: str, color: str, is_global: bool, created_at: datetime)`.
- `CategoryListResponse(items: list[CategoryOut])`.
- Repository exceptions: `DuplicateResourceError`, `ForbiddenResourceError`.
- `CategoryRepository.list/create/get/update/delete/clear` accepts JWT-derived `user_id`.
- `app.repositories` exports `category_repository` and the existing `transaction_repository` name.

- [ ] **Step 1: Create shared HTTP fixtures and failing category tests**

Move the unsigned-development token helpers and client into `backend/tests/conftest.py`. Provide fixtures `client`, `auth_headers`, `user_a_id`, `user_b_id`, and an autouse fixture that clears category/account/transaction repositories while restoring deterministic global categories.

Create `test_categories.py` covering this exact behavior:

```python
def test_category_crud(client, auth_headers):
    created = client.post(
        "/categories",
        headers=auth_headers(),
        json={"name": " Travel ", "color": "#2563eb"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Travel"
    assert body["color"] == "#2563EB"
    assert body["is_global"] is False

    listed = client.get("/categories", headers=auth_headers())
    assert listed.status_code == 200
    assert body["id"] in {item["id"] for item in listed.json()["items"]}

    updated = client.put(
        f"/categories/{body['id']}",
        headers=auth_headers(),
        json={"name": "Trips", "color": "#7c3aed"},
    )
    assert updated.status_code == 200
    assert updated.json()["color"] == "#7C3AED"
    assert client.delete(
        f"/categories/{body['id']}", headers=auth_headers()
    ).status_code == 204


def test_categories_include_defaults_but_exclude_other_users_custom_rows(
    client, auth_headers, user_a_id, user_b_id
):
    own = client.post(
        "/categories", headers=auth_headers(user_a_id),
        json={"name": "Own", "color": "#111827"},
    ).json()
    client.post(
        "/categories", headers=auth_headers(user_b_id),
        json={"name": "Other user", "color": "#6B7280"},
    )
    items = client.get(
        "/categories", headers=auth_headers(user_a_id)
    ).json()["items"]
    assert own["id"] in {item["id"] for item in items}
    assert "Other user" not in {item["name"] for item in items}
    assert {item["name"] for item in items if item["is_global"]} == {
        "Housing", "Groceries", "Dining", "Transport", "Utilities",
        "Health", "Entertainment", "Shopping", "Salary", "Other",
    }
```

Also test global update/delete `403`, cross-user update/delete `404`, duplicate custom name `409`, blank/81-character name `422`, invalid color `422`, malformed UUID `422`, and missing UUID `404`.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest tests/test_categories.py -q`.

Expected: failures because `/categories` and schemas/repositories do not exist.

- [ ] **Step 3: Add exact Pydantic category contracts**

Implement one reusable normalized name type and color validator:

```python
def normalize_name(value: str) -> str:
    normalized = value.strip()
    if not 1 <= len(normalized) <= 80:
        raise ValueError("name must contain between 1 and 80 characters")
    return normalized


def normalize_color(value: str) -> str:
    normalized = value.upper()
    if not re.fullmatch(r"#[0-9A-F]{6}", normalized):
        raise ValueError("color must use #RRGGBB format")
    return normalized
```

Apply them with Pydantic `field_validator` methods to `CategoryCreate` and `CategoryUpdate`; add the exact output/list schemas from Interfaces.

- [ ] **Step 4: Convert repositories to a package and implement categories**

Move transaction classes without behavior changes into `repositories/transactions.py`. `base.py` owns the psycopg connection context that sets `app.user_id`. `categories.py` defines a `CategoryRecord`, protocol, in-memory implementation seeded from an immutable ten-item tuple, and Postgres implementation.

List ordering is `(not is_global, name.casefold())`, so globals are first. Update/delete distinguish a visible global (`ForbiddenResourceError`) from absent/inaccessible (`None`). Duplicate inserts/updates raise `DuplicateResourceError`, including Postgres SQLSTATE `23505` translation.

`repositories/__init__.py` builds and exports repositories once according to `DATABASE_URL`, preserving `transaction_repository` for existing tests/routes.

- [ ] **Step 5: Add thin category routes and include them**

Implement:

```python
router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_model=CategoryListResponse)
def list_categories(user_id: UUID = Depends(get_current_user_id)) -> CategoryListResponse:
    return CategoryListResponse(
        items=[record.to_out() for record in category_repository.list(user_id)]
    )

@router.post("", response_model=CategoryOut, status_code=201)
def create_category(
    payload: CategoryCreate,
    user_id: UUID = Depends(get_current_user_id),
) -> CategoryOut:
    try:
        return category_repository.create(user_id, payload).to_out()
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail="Category name already exists") from error

@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    user_id: UUID = Depends(get_current_user_id),
) -> CategoryOut:
    try:
        record = category_repository.update(user_id, category_id, payload)
    except ForbiddenResourceError as error:
        raise HTTPException(status_code=403, detail="Global categories are read-only") from error
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail="Category name already exists") from error
    if record is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return record.to_out()

@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    try:
        deleted = category_repository.delete(user_id, category_id)
    except ForbiddenResourceError as error:
        raise HTTPException(status_code=403, detail="Global categories are read-only") from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
    return Response(status_code=204)
```

Translate duplicate to `409`, global mutation to `403`, missing/inaccessible to `404`, and return an empty `204` response.

- [ ] **Step 6: Verify GREEN and existing transaction compatibility**

Run:

```bash
cd backend
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest tests/test_categories.py tests/test_transactions.py -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
```

Expected: all selected tests pass; Ruff clean.

- [ ] **Step 7: Update progress and commit**

Record category backend completion in `context/progress-tracker.md`.

```bash
git add backend/app backend/tests context/progress-tracker.md
git commit -m "feat: add isolated category crud api"
```

---

### Task 3: Build account CRUD with isolation tests

**Owner:** Backend account agent

**Files:**
- Create: `backend/app/repositories/accounts.py`
- Create: `backend/app/routers/accounts.py`
- Create: `backend/tests/test_accounts.py`
- Modify: `backend/app/repositories/__init__.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Modify: `context/progress-tracker.md`

**Interfaces:**
- `AccountCreate(name: str)`, `AccountUpdate(name: str)`.
- `AccountOut(id: UUID, name: str, created_at: datetime)`.
- `AccountListResponse(items: list[AccountOut])`.
- `AccountRepository.list/create/get/update/delete/clear` scoped by JWT user.
- `app.repositories` exports `account_repository`.

- [ ] **Step 1: Write failing account HTTP tests**

Create tests for full CRUD, normalization, sorted listing, cross-user invisibility/mutation `404`, case-insensitive duplicate `409`, blank/81-character name `422`, malformed UUID `422`, and missing UUID `404`.

The main CRUD assertion is:

```python
def test_account_crud(client, auth_headers):
    created = client.post(
        "/accounts", headers=auth_headers(), json={"name": " Main checking "}
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Main checking"
    assert "user_id" not in body
    assert body["id"] in {
        item["id"] for item in client.get(
            "/accounts", headers=auth_headers()
        ).json()["items"]
    }
    assert client.put(
        f"/accounts/{body['id']}", headers=auth_headers(),
        json={"name": "Savings"},
    ).json()["name"] == "Savings"
    assert client.delete(
        f"/accounts/{body['id']}", headers=auth_headers()
    ).status_code == 204
```

- [ ] **Step 2: Verify RED**

Run: `cd backend && /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest tests/test_accounts.py -q`.

Expected: route/schema/repository failures.

- [ ] **Step 3: Implement account schemas, repository, and router**

Reuse `normalize_name` from schemas. Account repositories mirror category ownership mechanics without global rows or color. List sorts with `name.casefold()`. Translate SQLSTATE `23505` to `DuplicateResourceError`.

Expose `GET/POST /accounts` and `PUT/DELETE /accounts/{account_id}` with `200/201/204`, duplicate `409`, inaccessible/missing `404`, malformed UUID `422`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
cd backend
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest tests/test_accounts.py tests/test_categories.py -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
```

Expected: selected tests pass and Ruff clean.

- [ ] **Step 5: Update progress and commit**

```bash
git add backend/app backend/tests/test_accounts.py context/progress-tracker.md
git commit -m "feat: add isolated account crud api"
```

---

### Task 4: Enforce transaction references, account filtering, and delete nulling

**Owner:** Backend transaction-integration agent

**Files:**
- Modify: `backend/app/repositories/transactions.py`
- Modify: `backend/app/repositories/categories.py`
- Modify: `backend/app/repositories/accounts.py`
- Modify: `backend/app/routers/transactions.py`
- Modify: `backend/tests/test_transactions.py`
- Create: `backend/tests/test_phase2_postgres.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `context/progress-tracker.md`

**Interfaces:**
- `TransactionRepository.list(user_id: UUID, *, tx_type: TxType | None = None, category_id: UUID | None = None, account_id: UUID | None = None, date_from: date | None = None, date_to: date | None = None) -> list[TransactionRecord]`.
- `InvalidReferenceError(field: Literal["category_id", "account_id"])`.
- Transaction create/update returns `422` detail `{field} is not available to the current user` for inaccessible references.

- [ ] **Step 1: Write failing in-memory integration tests**

Expand transaction tests to create resources through their APIs, then assert:

```python
def test_transaction_accepts_global_or_owned_references(client, auth_headers):
    category_id = client.get(
        "/categories", headers=auth_headers()
    ).json()["items"][0]["id"]
    account_id = client.post(
        "/accounts", headers=auth_headers(), json={"name": "Checking"}
    ).json()["id"]
    response = client.post(
        "/transactions", headers=auth_headers(),
        json={
            "amount": "10.00", "type": "expense", "date": "2026-07-20",
            "category_id": category_id, "account_id": account_id,
        },
    )
    assert response.status_code == 201


def test_account_filter_and_resource_deletion_null_references(client, auth_headers):
    category = client.post(
        "/categories", headers=auth_headers(),
        json={"name": "Travel", "color": "#2563EB"},
    ).json()
    account = client.post(
        "/accounts", headers=auth_headers(), json={"name": "Card"}
    ).json()
    transaction = client.post(
        "/transactions", headers=auth_headers(),
        json={
            "amount": "20.00", "type": "expense", "date": "2026-07-20",
            "category_id": category["id"], "account_id": account["id"],
        },
    ).json()
    filtered = client.get(
        "/transactions", headers=auth_headers(),
        params={"account_id": account["id"]},
    ).json()["items"]
    assert [item["id"] for item in filtered] == [transaction["id"]]
    client.delete(f"/categories/{category['id']}", headers=auth_headers())
    client.delete(f"/accounts/{account['id']}", headers=auth_headers())
    fetched = client.get(
        f"/transactions/{transaction['id']}", headers=auth_headers()
    ).json()
    assert fetched["category_id"] is None
    assert fetched["account_id"] is None
```

Add two-user tests that another user's custom category/account produce `422`, and transaction list/get/update/delete remain isolated by JWT user.

- [ ] **Step 2: Verify RED**

Run: `cd backend && /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest tests/test_transactions.py -q`.

Expected: raw UUID behavior, missing account filter, and deletion-nulling assertions fail.

- [ ] **Step 3: Implement reference validation and account filtering**

In-memory transaction repository receives the built category/account repositories and calls `is_accessible(user_id, resource_id)` before create/update. Category/account delete methods call the in-memory transaction repository's `clear_category_reference` / `clear_account_reference` callbacks, or share a store object that performs the same atomic mutation.

Postgres create/update validates with scoped `SELECT EXISTS` queries in the same `_session` transaction before the write. Translate trigger SQLSTATE `23514` to `InvalidReferenceError`. Add `account_id` to list protocol, implementation conditions, router query argument, and query parameters.

- [ ] **Step 4: Add real Postgres RLS tests and CI database service**

`test_phase2_postgres.py` is marked `@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not configured")`. It applies `init.sql` to a disposable database connection, inserts two `auth.users`, sets `app.user_id` per transaction, and proves:

- user A reads globals and A rows but not B rows;
- A cannot update/delete B rows;
- users cannot update/delete global categories;
- cross-user transaction references raise `psycopg.errors.CheckViolation`;
- deleting owned category/account sets transaction columns null.

CI adds a Postgres 16 service, sets `TEST_DATABASE_URL`, runs Ruff, then pytest. Do not add a frontend test command; the project has none. Retain frontend lint/build steps.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
cd backend
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
```

Expected: all in-memory tests pass, Postgres tests skip only without `TEST_DATABASE_URL`, Ruff clean. When local Postgres is available, rerun with `TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@localhost:5432/finance_flow` and require the RLS tests to pass.

- [ ] **Step 6: Update progress and commit**

```bash
git add backend .github/workflows/ci.yml context/progress-tracker.md
git commit -m "feat: enforce transaction resource ownership"
```

---

### Task 5: Add shared frontend API modules and Categories management UI

**Owner:** Frontend categories agent

**Files:**
- Create: `frontend/lib/categories.ts`
- Create: `frontend/components/ui/select.tsx`
- Create: `frontend/components/ui/select.module.css`
- Create: `frontend/app/categories/categories-client.tsx`
- Create: `frontend/app/categories/categories.module.css`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/categories/page.tsx`
- Modify: `context/progress-tracker.md`

**Interfaces:**
- `requestJson<T>(path: string, init?: RequestInit): Promise<T>` in `lib/api.ts`.
- `Category { id; name; color; is_global; created_at }` and `CategoryListResponse { items }`.
- `listCategories`, `createCategory`, `updateCategory`, `deleteCategory`.
- Query key `categoryKeys.list(userId) => ["categories", userId] as const`.
- Reusable `Select` forwards native select props and supports a visible label.

- [ ] **Step 1: Establish the failing frontend contract checks**

Run before implementation:

```bash
cd frontend
rg 'function requestJson' lib/api.ts
rg 'CategoriesClient' app/categories/page.tsx
```

Expected: both commands exit 1 because the shared request helper and client page do not exist.

- [ ] **Step 2: Centralize authenticated JSON requests**

Move transaction-local request logic into `lib/api.ts`. The helper must merge auth headers, parse successful JSON, return `null as T` for `204`, and extract FastAPI errors as follows:

```typescript
interface FastApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
}

function errorMessage(body: FastApiErrorBody, fallback: string): string {
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    const messages = body.detail.flatMap((item) => item.msg ?? []);
    if (messages.length > 0) return messages.join(", ");
  }
  return fallback;
}
```

Catch invalid JSON and use `Request failed with status ${response.status}`.

- [ ] **Step 3: Implement strict category API functions and Select**

`categories.ts` exports exact DTOs and CRUD functions using `requestJson`. Create/update send JSON with `Content-Type: application/json`; delete expects `null`.

`Select` renders a label containing a visible text span and a native select that receives the forwarded `SelectHTMLAttributes<HTMLSelectElement>`. It renders optional error text and uses CSS Module styles with existing tokens.

- [ ] **Step 4: Implement CategoriesClient**

Follow the existing transaction auth gate. Query only when development fallback is active or a session exists. Use `session?.user.id ?? "development"` in the query key.

Render globals and customs separately. Modal state is `{ mode: "create" | "edit"; category?: Category } | null`. Form state is `{ name: string; color: string }`. Global cards have no edit/delete buttons. Custom delete opens a confirmation modal naming the category. On successful save/delete, close/reset modal and invalidate only `categoryKeys.list(userId)` and `transactions` queries.

Use visible labels, `required`, `maxLength={80}`, `pattern="#[0-9A-Fa-f]{6}"`, pending button text, inline error text, and color swatches whose background uses the API-provided validated hex color.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
cd frontend
npm run lint
npm run build
```

Expected: ESLint exits 0; Next build exits 0 and includes `/categories`.

- [ ] **Step 6: Update progress and commit**

```bash
git add frontend context/progress-tracker.md
git commit -m "feat: add category management ui"
```

---

### Task 6: Add Accounts management UI

**Owner:** Frontend accounts agent

**Files:**
- Create: `frontend/lib/accounts.ts`
- Create: `frontend/app/accounts/accounts-client.tsx`
- Create: `frontend/app/accounts/accounts.module.css`
- Modify: `frontend/app/accounts/page.tsx`
- Modify: `context/progress-tracker.md`

**Interfaces:**
- `Account { id; name; created_at }`, `AccountListResponse { items }`.
- `listAccounts`, `createAccount`, `updateAccount`, `deleteAccount`.
- Query key `accountKeys.list(userId) => ["accounts", userId] as const`.

- [ ] **Step 1: Verify the placeholder state is RED**

Run: `cd frontend && rg 'AccountsClient' app/accounts/page.tsx`.

Expected: exit 1.

- [ ] **Step 2: Implement account API module**

Use the shared `requestJson` helper. Create/update payloads are `{ name: string }`; delete expects `204`; list unwraps `{items}` only inside the component query function so the API module remains contract-explicit.

- [ ] **Step 3: Implement AccountsClient and page styles**

Use the same auth/query/mutation/modal interaction contract as CategoriesClient, without color/global sections. Render an accessible account list with Add, Edit, and Delete actions. Delete confirmation states that linked transactions remain but their account becomes `No account`. Successful mutations invalidate `accountKeys.list(userId)` and `transactions` queries.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
cd frontend
npm run lint
npm run build
```

Expected: both pass and build output includes `/accounts`.

- [ ] **Step 5: Update progress and commit**

```bash
git add frontend/app/accounts frontend/lib/accounts.ts context/progress-tracker.md
git commit -m "feat: add account management ui"
```

---

### Task 7: Connect transaction selectors and filters, then verify Phase 2

**Owner:** Frontend transaction-integration agent

**Files:**
- Modify: `frontend/app/transactions/transactions-client.tsx`
- Modify: `frontend/app/transactions/transactions.module.css`
- Modify: `frontend/lib/categories.ts`
- Modify: `frontend/lib/accounts.ts`
- Modify: `context/progress-tracker.md`
- Modify: `README.md`

**Interfaces:**
- `TransactionFilters` adds `accountId: string`.
- `buildQueryString` emits both `category_id` and `account_id`.
- Category/account query data supplies form selects, filter selects, and table labels.

- [ ] **Step 1: Establish failing selector/filter checks**

Run:

```bash
cd frontend
rg 'All accounts' app/transactions/transactions-client.tsx
rg 'account_id.*filters.accountId' app/transactions/transactions-client.tsx
```

Expected: both exit 1.

- [ ] **Step 2: Use shared requestJson and resource queries**

Delete the local request helper and import `requestJson`, category/account types, query keys, and list functions. Add resource queries enabled under the same auth condition as transactions and keyed by authenticated user ID. Include user ID in the transaction query key: `["transactions", userId, filters]`.

- [ ] **Step 3: Replace raw UUID fields with named selects**

The form options are:

```tsx
<option value="">Uncategorized</option>
{categories.map((category) => (
  <option key={category.id} value={category.id}>{category.name}</option>
))}
```

and:

```tsx
<option value="">No account</option>
{accounts.map((account) => (
  <option key={account.id} value={account.id}>{account.name}</option>
))}
```

Filter options use `All categories` and `All accounts`. Extend initial filters and query-string construction with `account_id`. Add a Clear filters button that restores the exact initial filter object.

- [ ] **Step 4: Render names and robust missing-reference fallbacks**

Build memoized `Map<string, string>` lookup tables. Table values are:

```typescript
const categoryLabel = item.category_id
  ? categoryNames.get(item.category_id) ?? "Unavailable category"
  : "Uncategorized";
const accountLabel = item.account_id
  ? accountNames.get(item.account_id) ?? "Unavailable account"
  : "No account";
```

Show resource-query errors through the existing error banner. Disable form submission while reference lists are loading so users cannot unknowingly submit stale UUID selections.

- [ ] **Step 5: Run complete automated verification**

Run:

```bash
cd backend
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest

cd ../frontend
npm run lint
npm run build
```

Expected: Ruff clean, all backend tests pass (only documented Postgres skip allowed when no integration URL), frontend lint/build exit 0.

- [ ] **Step 6: Perform local UI smoke test**

Start Postgres/backend/frontend using the documented Compose/local commands. In the signed-in UI:

1. Verify all ten global categories appear without mutation actions.
2. Create, edit, and delete one custom category.
3. Create, edit, and delete one account.
4. Create and edit a transaction using named category/account selectors.
5. Filter transactions by that category and account.
6. Delete the referenced custom resources and confirm the transaction remains with `Uncategorized` and `No account`.
7. Confirm another signed-in user cannot see the first user's custom rows.

Record exact smoke evidence and any environment limitations in `context/progress-tracker.md`; do not claim steps that were not observed.

- [ ] **Step 7: Finish docs and commit**

Mark Phase 2 complete only if automated checks and required smoke steps pass. Update README API/features if its current text is stale.

```bash
git add frontend/app/transactions frontend/lib context/progress-tracker.md README.md
git commit -m "feat: connect transactions to categories and accounts"
```

## Final Review Gate

After Tasks 1–7, generate a review package from the branch merge-base through `HEAD`. Dispatch an independent whole-branch reviewer against the approved design spec and this plan. Resolve every Critical/Important finding with one focused fix agent, rerun affected tests, regenerate the review package, and obtain a clean re-review.

Do not merge automatically. Present the verified branch, commit list, test results, smoke evidence, and PR-ready summary to the user.
