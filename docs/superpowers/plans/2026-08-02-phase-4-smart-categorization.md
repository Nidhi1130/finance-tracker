# Phase 4 Smart Categorization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically categorize newly created transactions using user-owned keyword rules first and an OpenAI structured-output fallback second, while preserving manual control and per-user isolation.

**Architecture:** Extend the existing repository layer and RLS schema with categorization rules and guarded transaction status updates. A focused categorization service coordinates deterministic matching and a provider protocol; the OpenAI adapter is server-only and runs inside FastAPI background tasks. The frontend adds a Rules manager and transaction status/correction flows through user-scoped TanStack Query clients.

**Tech Stack:** PostgreSQL 16/Supabase RLS, FastAPI, Pydantic, psycopg 3, OpenAI Python SDK Responses API, pytest, Next.js 16, React 19, TypeScript, TanStack Query 5, Vitest, Testing Library, CSS Modules.

## Global Constraints

- Priority is always manual selection, matching user rule, OpenAI fallback, then uncategorized.
- Rule matching is case-insensitive substring matching; the longest keyword wins, followed by normalized keyword and rule ID.
- Never automatically create a rule from a correction; the user must confirm “Save this as a rule.”
- Never send amount, account data, user ID, JWT, or API credentials to OpenAI.
- `OPENAI_API_KEY` is server-only; `OPENAI_CATEGORIZATION_MODEL` defaults to `gpt-5.6-luna`.
- The OpenAI response may contain only an allowed category ID or null and must be validated again by the backend.
- Transaction creation must persist before categorization begins; FastAPI `BackgroundTasks` is sufficient and no external queue is added.
- A background result must never overwrite a manual category selected after the task started.
- All application queries remain scoped to the verified Supabase JWT `sub`, with forced RLS as defense in depth.
- Frontend query keys include the authenticated user ID; the frontend calls FastAPI only.
- CI uses fake providers and never calls OpenAI.
- Add migration `004`; do not edit already-applied migrations `002` or `003`.
- Backend verification uses Ruff `0.15.21`, the full PostgreSQL test suite, and no user-owned service on port 5432 is stopped or replaced.

---

### Task 1: Phase 4 schema, transaction metadata, and RLS migration

**Files:**
- Create: `backend/sql/migrations/004_phase_4_smart_categorization.sql`
- Modify: `backend/sql/init.sql`
- Modify: `backend/app/schemas.py`
- Modify: `backend/tests/test_phase2_sql.py`
- Modify: `backend/tests/test_phase2_postgres.py`

**Interfaces:**
- Produces: `CategorizationSource`, `CategorizationStatus`, `CategorizationRuleCreate`, `CategorizationRuleUpdate`, `CategorizationRuleOut`, and `CategorizationRuleListResponse` in `app.schemas`.
- Extends: `TransactionOut` with `category_source`, `categorization_status`, and `categorized_at`.
- Produces database table `categorization_rules` and transaction columns consumed by Tasks 2–4.

- [ ] **Step 1: Write failing SQL and schema contract tests**

Add assertions to `test_phase2_sql.py` for migration `004` and focused PostgreSQL tests proving:

```python
def test_phase4_migration_defines_rules_rls_and_transaction_metadata() -> None:
    sql = PHASE4_MIGRATION.read_text()
    assert "create table if not exists categorization_rules" in sql.lower()
    assert "alter table categorization_rules force row level security" in sql.lower()
    assert "category_source" in sql
    assert "categorization_status" in sql
    assert "on delete cascade" in sql.lower()


def test_phase4_migration_is_idempotent_and_backfills_transactions(postgres_url: str) -> None:
    apply_sql(postgres_url, PHASE4_MIGRATION)
    apply_sql(postgres_url, PHASE4_MIGRATION)
    # Insert one categorized and one uncategorized legacy-shaped row before
    # applying the migration in the fixture, then assert manual/categorized
    # and null/not_requested respectively.
```

Add Pydantic tests that serialize exact enum strings and reject a blank or 121-character keyword.

- [ ] **Step 2: Run the focused tests to verify RED**

Run:

```bash
cd backend
TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@127.0.0.1:5433/finance_flow \
  PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest \
  tests/test_phase2_sql.py tests/test_phase2_postgres.py -q
```

Expected: failures because migration `004`, the rule table, and schema types do not exist.

- [ ] **Step 3: Add Pydantic types and transaction response fields**

Add these public shapes to `schemas.py`:

```python
class CategorizationSource(str, Enum):
    manual = "manual"
    rule = "rule"
    openai = "openai"


class CategorizationStatus(str, Enum):
    not_requested = "not_requested"
    pending = "pending"
    categorized = "categorized"
    failed = "failed"


def normalize_keyword(value: str) -> str:
    normalized = " ".join(value.split())
    if not 1 <= len(normalized) <= 120:
        raise ValueError("keyword must contain between 1 and 120 characters")
    return normalized


def normalize_optional_keyword(value: str | None) -> str | None:
    return normalize_keyword(value) if value is not None else None


class CategorizationRuleCreate(BaseModel):
    keyword: str
    category_id: UUID
    enabled: bool = True
    _normalize_keyword = field_validator("keyword")(normalize_keyword)


class CategorizationRuleUpdate(BaseModel):
    keyword: str | None = None
    category_id: UUID | None = None
    enabled: bool | None = None
    _normalize_keyword = field_validator("keyword")(normalize_optional_keyword)


class CategorizationRuleOut(BaseModel):
    id: UUID
    keyword: str
    category_id: UUID
    category_name: str
    category_color: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class CategorizationRuleListResponse(BaseModel):
    items: list[CategorizationRuleOut]
```

Extend `TransactionOut` with nullable source/time and a required status.

- [ ] **Step 4: Implement the idempotent migration and fresh-install schema**

Migration `004` must:

```sql
begin;

alter table transactions
  add column if not exists category_source text,
  add column if not exists categorization_status text not null default 'not_requested',
  add column if not exists categorized_at timestamptz;

update transactions
set category_source = 'manual',
    categorization_status = 'categorized',
    categorized_at = coalesce(categorized_at, updated_at)
where category_id is not null
  and category_source is null;

create table if not exists categorization_rules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  keyword text not null check (char_length(btrim(keyword)) between 1 and 120),
  category_id uuid not null references categories(id) on delete cascade,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists categorization_rules_user_lower_keyword_key
  on categorization_rules (user_id, lower(keyword));
```

Add/drop named check constraints idempotently for the source and status enums. Add `enforce_categorization_rule_category_ownership()` as a `SECURITY DEFINER` trigger with a fixed `search_path`; it accepts only global categories or categories owned by `new.user_id`. Enable and force RLS with an own-row `FOR ALL` policy using the existing `app.user_id` setting. Mirror the final schema in `init.sql`.

- [ ] **Step 5: Run focused and full backend checks**

Run the focused command from Step 2, then:

```bash
TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@127.0.0.1:5433/finance_flow \
  PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
```

Expected: all tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 6: Commit the schema unit**

```bash
git add backend/sql backend/app/schemas.py backend/tests/test_phase2_sql.py backend/tests/test_phase2_postgres.py
git commit -m "feat: add smart categorization schema"
```

---

### Task 2: Categorization rule repository and authenticated CRUD API

**Files:**
- Create: `backend/app/repositories/categorization_rules.py`
- Create: `backend/app/routers/categorization_rules.py`
- Create: `backend/tests/test_categorization_rules.py`
- Modify: `backend/app/repositories/__init__.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/test_phase2_postgres.py`

**Interfaces:**
- Consumes: rule Pydantic types and table from Task 1.
- Produces: `CategorizationRuleRecord`, `CategorizationRuleRepository`, `InMemoryCategorizationRuleRepository`, `PostgresCategorizationRuleRepository`, and singleton `categorization_rule_repository`.
- Produces: authenticated CRUD under `/categorization-rules` for Tasks 3, 5, and 6.

- [ ] **Step 1: Write failing CRUD, validation, and isolation tests**

Cover create/list/update/delete, duplicate keywords differing only by case,
unavailable category IDs, immutable cross-user rows, deterministic ordering,
and enable/disable behavior:

```python
def test_rules_are_isolated_by_authenticated_user(client, auth_headers, global_category_id):
    created = client.post(
        "/categorization-rules",
        headers=auth_headers(USER_A_ID),
        json={"keyword": "spotify", "category_id": global_category_id},
    )
    assert created.status_code == 201
    other = client.get("/categorization-rules", headers=auth_headers(USER_B_ID))
    assert other.json() == {"items": []}


def test_rule_keyword_is_case_insensitively_unique(...):
    # Create "Spotify", then assert "spotify" returns 409.
```

Extend PostgreSQL integration coverage so a non-bypass role cannot read or
mutate another user’s rule and the ownership trigger rejects User B’s private
category for User A.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd backend
PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest \
  tests/test_categorization_rules.py -q
```

Expected: import/404 failures because the repository and router do not exist.

- [ ] **Step 3: Implement repository records and protocols**

Use this boundary:

```python
@dataclass
class CategorizationRuleRecord:
    id: UUID
    user_id: UUID
    keyword: str
    category_id: UUID
    category_name: str
    category_color: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class CategorizationRuleRepository(Protocol):
    def list(self, user_id: UUID, *, enabled_only: bool = False) -> list[CategorizationRuleRecord]: ...
    def create(self, user_id: UUID, payload: CategorizationRuleCreate) -> CategorizationRuleRecord: ...
    def get(self, user_id: UUID, rule_id: UUID) -> CategorizationRuleRecord | None: ...
    def update(self, user_id: UUID, rule_id: UUID, payload: CategorizationRuleUpdate) -> CategorizationRuleRecord | None: ...
    def delete(self, user_id: UUID, rule_id: UUID) -> bool: ...
    def clear(self) -> None: ...
```

Both implementations validate category accessibility. Postgres writes use
one `database_session` per operation and translate unique violations into
`DuplicateResourceError` and invalid category references into
`InvalidReferenceError("category_id")`.

- [ ] **Step 4: Add the thin authenticated router and singleton wiring**

Implement exact status behavior:

- list `200` with `{items: [...]}`;
- create `201`;
- update `200`;
- delete `204`;
- duplicate `409`;
- unavailable category `422`;
- missing/cross-user row `404`.

Register the router in `main.py`, export the repository in
`repositories/__init__.py`, and clear the in-memory repository in the autouse
test fixture.

- [ ] **Step 5: Run focused, PostgreSQL, and full backend verification**

Run:

```bash
TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@127.0.0.1:5433/finance_flow \
  PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest \
  tests/test_categorization_rules.py tests/test_phase2_postgres.py -q
TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@127.0.0.1:5433/finance_flow \
  PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
```

- [ ] **Step 6: Commit the rules API**

```bash
git add backend/app backend/tests
git commit -m "feat: add categorization rule api"
```

---

### Task 3: Deterministic matcher and OpenAI provider boundary

**Files:**
- Create: `backend/app/services/categorization.py`
- Create: `backend/app/providers/__init__.py`
- Create: `backend/app/providers/openai_categorization.py`
- Create: `backend/tests/test_categorization.py`
- Create: `backend/tests/test_openai_categorization.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Modify: `.env.example`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: `CategorizationRuleRecord`, `CategoryRecord`, and `TxType`.
- Produces: `CategoryCandidate`, `CategorizationProvider`, `match_rule()`, and `OpenAICategorizationProvider`.
- The orchestration method that writes transactions is deferred to Task 4; this task establishes a tested pure/provider boundary.

- [ ] **Step 1: Write failing matcher tests**

Use hand-derived fixtures proving case-insensitive substring behavior, longest
match precedence, disabled-rule exclusion, deterministic tie-breaking, and no
description/no-match behavior:

```python
def test_match_rule_prefers_longest_keyword() -> None:
    rules = [rule("uber", RULE_A), rule("uber eats", RULE_B)]
    assert match_rule("UBER EATS STOCKHOLM", rules).id == RULE_B


def test_match_rule_breaks_equal_length_ties_by_keyword_then_id() -> None:
    # Reverse the fixture input and assert the same winning rule.
```

- [ ] **Step 2: Write failing OpenAI adapter tests with a fake SDK client**

Tests must assert the provider sends description, type, and only category
ID/name pairs; verify amount, account, user ID, and secrets are absent. Cover
allowed ID, null, refusal, malformed output, foreign ID, timeout, and SDK
error. No test may call the network.

- [ ] **Step 3: Run tests to verify RED**

```bash
cd backend
PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest \
  tests/test_categorization.py tests/test_openai_categorization.py -q
```

Expected: missing service/provider imports.

- [ ] **Step 4: Implement the pure matcher and provider protocol**

```python
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
    matches = [rule for rule in rules if rule.enabled and rule.keyword.casefold() in folded]
    return min(matches, key=lambda rule: (-len(rule.keyword), rule.keyword.casefold(), str(rule.id)), default=None)
```

- [ ] **Step 5: Add and lock the OpenAI SDK, then implement structured output**

Use `uv add 'openai>=2,<3'` from `backend/` so `pyproject.toml` and `uv.lock`
are generated together. Define a private Pydantic response model containing
`category_id: UUID | None`. Use the Responses API structured parse helper and
validate `output_parsed.category_id` against the candidate ID set before
returning it. Translate refusal/timeout/provider/validation failures into a
single typed `CategorizationProviderError` without logging prompt content.

Add to `.env.example` and Docker backend environment:

```dotenv
OPENAI_API_KEY=
OPENAI_CATEGORIZATION_MODEL=gpt-5.6-luna
OPENAI_CATEGORIZATION_TIMEOUT_SECONDS=8
```

- [ ] **Step 6: Run provider tests, lock validation, and Ruff**

```bash
cd backend
UV_CACHE_DIR=/tmp/finance-tracker-phase4-uv-cache uv lock --check
PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest \
  tests/test_categorization.py tests/test_openai_categorization.py -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
```

- [ ] **Step 7: Commit the matcher/provider unit**

```bash
git add backend/app/services/categorization.py backend/app/providers backend/tests/test_categorization.py backend/tests/test_openai_categorization.py backend/pyproject.toml backend/uv.lock .env.example docker-compose.yml
git commit -m "feat: add openai categorization provider"
```

---

### Task 4: Background transaction categorization and guarded retry

**Files:**
- Modify: `backend/app/repositories/transactions.py`
- Modify: `backend/app/repositories/__init__.py`
- Modify: `backend/app/services/categorization.py`
- Modify: `backend/app/services/__init__.py`
- Modify: `backend/app/routers/transactions.py`
- Modify: `backend/tests/test_transactions.py`
- Modify: `backend/tests/test_categorization.py`
- Modify: `backend/tests/test_phase2_postgres.py`

**Interfaces:**
- Consumes: rule repository, category repository, provider protocol, transaction metadata, and matcher from Tasks 1–3.
- Produces: `CategorizationService.categorize(user_id, transaction_id)` and `POST /transactions/{id}/categorize`.
- Extends `TransactionRepository` with guarded status transition methods used only by the service/router.

- [ ] **Step 1: Write failing transaction lifecycle tests**

Cover these exact outcomes:

```python
def test_manual_category_creation_does_not_schedule_background_work(...): ...
def test_uncategorized_creation_returns_pending_and_schedules_work(...): ...
def test_rule_match_assigns_rule_source_without_calling_provider(...): ...
def test_openai_fallback_assigns_openai_source(...): ...
def test_manual_update_wins_over_late_background_result(...): ...
def test_provider_failure_marks_failed_without_changing_category(...): ...
def test_retry_returns_202_and_rejects_manual_transaction_with_409(...): ...
```

Use a spy/fake service at the router boundary and a fake provider at the
service boundary. Add a PostgreSQL test in which an automatic guarded update
returns no row after a manual category update committed first.

- [ ] **Step 2: Run focused tests to verify RED**

```bash
cd backend
PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest \
  tests/test_transactions.py tests/test_categorization.py -q
```

Expected: missing transaction metadata/guard methods and retry route.

- [ ] **Step 3: Extend transaction records and repository protocol**

Add metadata fields to `TransactionRecord`, every SQL projection, row mapper,
and `to_out()`. Define these protocol methods:

```python
def prepare_categorization(self, user_id: UUID, transaction_id: UUID) -> TransactionRecord | None: ...

def apply_automatic_category(
    self,
    user_id: UUID,
    transaction_id: UUID,
    category_id: UUID,
    source: CategorizationSource,
) -> TransactionRecord | None: ...

def finish_without_category(
    self,
    user_id: UUID,
    transaction_id: UUID,
    status: CategorizationStatus,
) -> TransactionRecord | None: ...
```

Postgres automatic updates must include:

```sql
where id = %s
  and user_id = current_setting('app.user_id')::uuid
  and category_id is null
  and categorization_status = 'pending'
```

Manual create/update sets manual/categorized/time. Explicitly clearing a
category sets null/not_requested/null. In-memory behavior must match.

- [ ] **Step 4: Implement categorization orchestration**

Construct `CategorizationService` with transaction, rule, category, and
optional provider dependencies. `categorize()` reloads the pending record,
tries `match_rule`, then the provider, and writes only through guarded methods.
No description or no provider result finishes as `not_requested`; missing key
or provider error finishes as `failed`. Rule matches never call the provider.

Build the service singleton in `services/__init__.py`; construct the OpenAI
provider only when `OPENAI_API_KEY` exists.

- [ ] **Step 5: Wire FastAPI background tasks and retry**

Add `BackgroundTasks` to create and retry handlers:

```python
record = repository.create(user_id, payload)
if payload.category_id is None:
    background_tasks.add_task(categorization_service.categorize, user_id, record.id)
return record.to_out()
```

Retry calls `prepare_categorization`; return 404 for inaccessible/missing, 409
when a manual category exists, otherwise enqueue and return `202` with the
pending transaction.

- [ ] **Step 6: Run focused, PostgreSQL, and full backend verification**

```bash
TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@127.0.0.1:5433/finance_flow \
  PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest \
  tests/test_transactions.py tests/test_categorization.py tests/test_phase2_postgres.py -q
TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@127.0.0.1:5433/finance_flow \
  PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
```

- [ ] **Step 7: Commit background categorization**

```bash
git add backend/app backend/tests
git commit -m "feat: categorize transactions in background"
```

---

### Task 5: Rules API client and authenticated Rules page

**Files:**
- Create: `frontend/lib/categorization-rules.ts`
- Create: `frontend/lib/categorization-rules.test.ts`
- Create: `frontend/components/rules/rules-manager.tsx`
- Create: `frontend/components/rules/rules-manager.module.css`
- Create: `frontend/components/rules/rules-manager.test.tsx`
- Create: `frontend/app/rules/page.tsx`
- Modify: `frontend/components/layout/app-shell-nav.tsx`

**Interfaces:**
- Consumes: `/categorization-rules` API and category list from Tasks 2 and 4.
- Produces: typed rule API functions, `categorizationRuleQueryKey(userId)`, and authenticated `<RulesManager />`.
- Supplies `createCategorizationRule()` to Task 6’s correction flow.

- [ ] **Step 1: Write failing API-client tests**

Assert exact user-scoped key and request shapes:

```typescript
expect(categorizationRuleQueryKey("user-a")).toEqual(["categorization-rules", "user-a"]);
await createCategorizationRule({ keyword: "spotify", category_id: "category-1", enabled: true });
expect(requestJson).toHaveBeenCalledWith("/categorization-rules", expect.objectContaining({ method: "POST" }));
```

Define public TypeScript types mirroring `CategorizationRuleOut` exactly.

- [ ] **Step 2: Write failing RulesManager behavior tests**

With a real `QueryClientProvider` and narrow mocks for auth/router/API, test:

- authenticated list and empty state;
- create with keyword/category;
- edit;
- enable/disable;
- delete confirmation;
- validation/API error;
- User A to User B query-key isolation.

- [ ] **Step 3: Run tests to verify RED**

```bash
cd frontend
npm test -- lib/categorization-rules.test.ts components/rules/rules-manager.test.tsx
```

Expected: missing module/component failures.

- [ ] **Step 4: Implement the typed API client**

Export:

```typescript
export interface CategorizationRule {
  id: string;
  keyword: string;
  category_id: string;
  category_name: string;
  category_color: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export function categorizationRuleQueryKey(userId: string) {
  return ["categorization-rules", userId] as const;
}
```

Add `listCategorizationRules`, `createCategorizationRule`,
`updateCategorizationRule`, and `deleteCategorizationRule`, all through
`requestJson`.

- [ ] **Step 5: Implement RulesManager and route**

Follow existing auth cards and modal primitives. The create/edit form has
Keyword, Category, and Enabled. Display category color/name and status. Use
exact user-scoped invalidation; category choices come from
`categoryQueryKey(userId)`. Add `{ href: "/rules", label: "Rules" }` to the
primary navigation and keep `app/rules/page.tsx` a thin `AppShellNav` wrapper.

- [ ] **Step 6: Run frontend tests, lint, and build**

```bash
cd frontend
npm test
npm run lint
npm run build
```

- [ ] **Step 7: Commit the Rules UI**

```bash
git add frontend/lib/categorization-rules.ts frontend/lib/categorization-rules.test.ts frontend/components/rules frontend/app/rules frontend/components/layout/app-shell-nav.tsx
git commit -m "feat: add categorization rules manager"
```

---

### Task 6: Transaction Auto states, polling, retry, and correction-to-rule flow

**Files:**
- Create: `frontend/lib/transactions.ts`
- Create: `frontend/lib/transactions.test.ts`
- Create: `frontend/app/transactions/transactions-client.test.tsx`
- Modify: `frontend/app/transactions/transactions-client.tsx`
- Modify: `frontend/app/transactions/transactions.module.css`

**Interfaces:**
- Consumes: transaction metadata/retry endpoint from Task 4 and rule creation client from Task 5.
- Produces: user-scoped transaction query helpers and complete Phase 4 transaction UX.

- [ ] **Step 1: Extract and test a typed transaction API boundary**

Move API types and request helpers out of the component. Export:

```typescript
export type CategorizationSource = "manual" | "rule" | "openai" | null;
export type CategorizationStatus = "not_requested" | "pending" | "categorized" | "failed";

export interface Transaction {
  // existing fields
  category_source: CategorizationSource;
  categorization_status: CategorizationStatus;
  categorized_at: string | null;
}

export function transactionQueryKey(userId: string, filters: TransactionFilters) {
  return ["transactions", userId, filters] as const;
}
```

Test query-string encoding, create/update request shapes, retry path/method,
and user-scoped keys.

- [ ] **Step 2: Write failing component tests for Phase 4 states**

Use a real QueryClient and fake timers where polling is involved. Assert:

- category empty option reads `Auto categorize`;
- pending row says `Categorizing…` and enables bounded refetching;
- rule/OpenAI results show an accessible Auto badge naming the source;
- manual result has no Auto badge;
- failed row shows Retry and invokes `POST /transactions/{id}/categorize`;
- automatic category correction saves manual first, then offers rule creation;
- dismissing the rule offer does not undo the correction;
- a missing description does not show the correction-to-rule offer;
- A-to-B session change does not display A’s transactions.

- [ ] **Step 3: Run tests to verify RED**

```bash
cd frontend
npm test -- lib/transactions.test.ts app/transactions/transactions-client.test.tsx
```

Expected: missing API boundary and Phase 4 UI assertions fail.

- [ ] **Step 4: Use the typed client and bounded pending polling**

Replace inline `requestJson` calls with `listTransactions`,
`saveTransaction`, `deleteTransaction`, and `retryCategorization`. Configure:

```typescript
refetchInterval: (query) =>
  query.state.data?.some((item) => item.categorization_status === "pending")
    ? 1500
    : false,
```

Invalidate only `['transactions', userId]` after mutations. Retry invalidates
the same prefix after its `202` response.

- [ ] **Step 5: Render source/status and correction UI**

Keep the table stable while pending. Render an Auto badge for rule/OpenAI with
screen-reader text `Automatically categorized by saved rule` or
`Automatically categorized by OpenAI`. Failed rows keep `Uncategorized` and a
Retry button.

Before an edit, retain the original transaction. After a successful category
change from `rule` or `openai`, open a rule modal if description exists. Suggest:

```typescript
export function suggestRuleKeyword(description: string): string {
  return description.trim().replace(/\s+/g, " ").toLocaleLowerCase().slice(0, 120);
}
```

The editable modal calls `createCategorizationRule`; Cancel only closes it.
The transaction is already manual regardless of rule creation outcome.

- [ ] **Step 6: Run full frontend verification**

```bash
cd frontend
npm test
npm run lint
npm run build
```

- [ ] **Step 7: Commit transaction UX**

```bash
git add frontend/lib/transactions.ts frontend/lib/transactions.test.ts frontend/app/transactions
git commit -m "feat: show automatic transaction categories"
```

---

### Task 7: Supabase deployment, provider smoke test, documentation, and final verification

**Files:**
- Create: `context/feature-specs/06-smart-categorization.md`
- Modify: `context/architecture.md`
- Modify: `context/progress-tracker.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: all completed Phase 4 units.
- Produces: deployed migration `004`, verified OpenAI configuration, current documentation, and final evidence.

- [ ] **Step 1: Apply only migration 004 to Supabase**

Read the configured remote `DATABASE_URL` without printing it. Execute only
`backend/sql/migrations/004_phase_4_smart_categorization.sql`. Verify table,
columns, forced RLS, policies, trigger, unique index, and transaction backfill
through read-only catalog queries. Do not re-run prior migrations or modify
application data manually.

- [ ] **Step 2: Run the complete backend verification**

Against the isolated PostgreSQL test service on port 5433:

```bash
cd backend
TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@127.0.0.1:5433/finance_flow \
  PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
UV_CACHE_DIR=/tmp/finance-tracker-phase4-uv-cache uv lock --check
```

Record exact pass/skip/warning counts.

- [ ] **Step 3: Run the complete frontend verification**

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
```

Record exact test counts and existing audit/deprecation warnings separately
from failures.

- [ ] **Step 4: Run a server-side OpenAI smoke test**

With a user-supplied server-side `OPENAI_API_KEY`, call the provider using a
dedicated description such as `SPOTIFY TEST PURCHASE`, type `expense`, and a
small allowed candidate list. Verify the returned value is one supplied ID or
null. Do not print the key, raw request headers, or full provider response. If
the key is unavailable, stop and record this as a Phase 4 completion blocker
rather than claiming the smoke test passed.

- [ ] **Step 5: Perform authenticated UI smoke coverage**

Verify in two signed-in sessions:

1. manual category bypasses automation;
2. `spotify` rule categorizes a matching transaction and shows Auto/rule;
3. unmatched description uses OpenAI and shows Auto/OpenAI;
4. a late background result cannot overwrite a manual edit;
5. provider failure shows Retry and retry recovers;
6. a correction remains saved when “Save this as a rule” is dismissed;
7. accepting the offer creates an editable rule visible on `/rules`;
8. User B cannot see User A’s rules, transactions, or cached data.

Record any unavailable browser/session scenario explicitly.

- [ ] **Step 6: Update Phase 4 documentation**

Create the feature spec with final API/schema/state behavior. Update
architecture with the rules table, provider boundary, and background guard.
Update progress to Phase 4 and preserve unresolved Phase 2/3 smoke gaps. Update
README environment variables and local setup without exposing credentials.

- [ ] **Step 7: Run final repository checks and commit docs**

```bash
git diff --check
git status --short
git log --oneline --decorate -12
git add context README.md
git commit -m "docs: record phase 4 smart categorization"
```

- [ ] **Step 8: Request final whole-branch review**

Review from the Phase 3 head through the Phase 4 documentation commit for
spec coverage, RLS/user isolation, concurrency, provider data minimization,
frontend cache isolation, accessibility, and truthful smoke-test reporting.
Address every accepted finding with focused regression coverage, then rerun
the complete backend and frontend verification before publishing.
