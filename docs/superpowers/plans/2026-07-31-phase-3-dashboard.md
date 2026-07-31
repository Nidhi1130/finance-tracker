# Phase 3 Insights Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an authenticated dashboard at `/` that returns and visualizes user-isolated income, expense, net, expense-by-category, and time-series insights for a selected period.

**Architecture:** Add one FastAPI `GET /dashboard` endpoint backed by a dedicated dashboard service and in-memory/PostgreSQL repositories. PostgreSQL performs parameterized server-side aggregation inside the existing user-scoped database session; the Next.js client fetches the single response through TanStack Query and renders period controls, summary cards, and Recharts visualizations.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, psycopg 3, PostgreSQL 16/17, Supabase Auth/RLS, Next.js 16, React 19, TypeScript, TanStack Query 5, Recharts 3.10.1, Vitest 3.2.7, React Testing Library 16.3.2, CSS Modules

## Global Constraints

- The frontend calls FastAPI only; it never calls Supabase or PostgreSQL directly.
- The verified Supabase JWT `sub` is the only source of `user_id`.
- Every dashboard SQL query includes the current user and inclusive date range, and runs inside `database_session()` so `app.user_id` and RLS remain active.
- Do not create a database view, RPC, or `SECURITY DEFINER` function for dashboard aggregation.
- Money and percentages use PostgreSQL `numeric` and Python `Decimal`; never use float for financial calculations.
- `GET /dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD` defaults missing dates to the current UTC calendar month and returns `422` for malformed or reversed ranges.
- Dashboard account scope is all accounts; Phase 3 does not add an account filter.
- Bucket thresholds are inclusive-period length: daily for 1–31 days, weekly for 32–90 days, monthly for 91+ days; weeks start Monday.
- Only expenses contribute to category breakdown; missing categories use `Uncategorized` and `#6B7280`.
- TanStack Query keys include authenticated user ID plus both resolved dates.
- Frontend styles use CSS Modules and existing design tokens; do not add Tailwind or a component library.
- Preserve unrelated Phase 2 work in `/private/tmp/finance-tracker-phase2`; all Phase 3 changes stay in `/private/tmp/finance-tracker-phase3` on `codex/phase-3-dashboard`.

---

### Task 1: Dashboard contract, service, in-memory repository, and route

**Files:**
- Create: `backend/app/repositories/dashboard.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/dashboard.py`
- Create: `backend/app/routers/dashboard.py`
- Create: `backend/tests/test_dashboard.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/repositories/__init__.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `DashboardBucket`, `DashboardPeriod`, `DashboardSummary`, `DashboardCategory`, `DashboardTrendPoint`, and `DashboardResponse` Pydantic models.
- Produces: `DashboardRepository.get(user_id: UUID, date_from: date, date_to: date, bucket: DashboardBucket) -> DashboardRecord`.
- Produces: `select_bucket(date_from: date, date_to: date) -> DashboardBucket` and `get_dashboard(repository, user_id, date_from, date_to) -> DashboardResponse`.
- Produces: authenticated `GET /dashboard` with optional `from` and `to` query parameters.

- [ ] **Step 1: Write failing endpoint and bucket-selection tests**

Create `backend/tests/test_dashboard.py` with helpers that use existing transaction/category APIs and assertions equivalent to:

```python
from datetime import date
from fastapi.testclient import TestClient

from app.schemas import DashboardBucket
from app.services.dashboard import select_bucket


def test_dashboard_summary_categories_and_trend(client: TestClient, auth_headers) -> None:
    headers = auth_headers()
    groceries = next(
        item
        for item in client.get("/categories", headers=headers).json()["items"]
        if item["name"] == "Groceries"
    )
    for payload in (
        {"amount": "1200.00", "type": "income", "date": "2026-07-01", "description": "Salary"},
        {"amount": "300.00", "type": "expense", "date": "2026-07-02", "description": "Food", "category_id": groceries["id"]},
        {"amount": "100.00", "type": "expense", "date": "2026-07-02", "description": "Unknown"},
        {"amount": "999.00", "type": "expense", "date": "2026-06-30", "description": "Outside"},
    ):
        assert client.post("/transactions", headers=headers, json=payload).status_code == 201

    response = client.get(
        "/dashboard",
        headers=headers,
        params={"from": "2026-07-01", "to": "2026-07-31"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["period"] == {"from": "2026-07-01", "to": "2026-07-31", "bucket": "daily"}
    assert body["summary"] == {"income": "1200.00", "expense": "400.00", "net": "800.00"}
    assert [(item["name"], item["amount"], item["percentage"]) for item in body["categories"]] == [
        ("Groceries", "300.00", "75.00"),
        ("Uncategorized", "100.00", "25.00"),
    ]
    assert body["trend"] == [
        {"period_start": "2026-07-01", "label": "1 Jul", "income": "1200.00", "expense": "0.00"},
        {"period_start": "2026-07-02", "label": "2 Jul", "income": "0.00", "expense": "400.00"},
    ]


def test_bucket_thresholds() -> None:
    assert select_bucket(date(2026, 1, 1), date(2026, 1, 31)) is DashboardBucket.daily
    assert select_bucket(date(2026, 1, 1), date(2026, 2, 1)) is DashboardBucket.weekly
    assert select_bucket(date(2026, 1, 1), date(2026, 3, 31)) is DashboardBucket.weekly
    assert select_bucket(date(2026, 1, 1), date(2026, 4, 1)) is DashboardBucket.monthly
```

Add tests in the same file for an empty period, a reversed range returning `422`, malformed dates returning `422`, current-month defaults by monkeypatching `app.routers.dashboard.utc_today`, and User B data not appearing for User A.

- [ ] **Step 2: Run the new tests and confirm the expected failure**

Run:

```bash
cd backend
PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest tests/test_dashboard.py -q
```

Expected: collection or request failure because dashboard schemas/service/route do not exist.

- [ ] **Step 3: Add the exact dashboard response schemas**

Extend `backend/app/schemas.py` with:

```python
from pydantic import BaseModel, ConfigDict, Field


class DashboardBucket(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class DashboardPeriod(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    date_from: Date = Field(alias="from")
    date_to: Date = Field(alias="to")
    bucket: DashboardBucket


class DashboardSummary(BaseModel):
    income: Decimal
    expense: Decimal
    net: Decimal


class DashboardCategory(BaseModel):
    category_id: UUID | None
    name: str
    color: str
    amount: Decimal
    percentage: Decimal


class DashboardTrendPoint(BaseModel):
    period_start: Date
    label: str
    income: Decimal
    expense: Decimal


class DashboardResponse(BaseModel):
    period: DashboardPeriod
    summary: DashboardSummary
    categories: list[DashboardCategory]
    trend: list[DashboardTrendPoint]
```

- [ ] **Step 4: Implement repository records and the in-memory repository**

Create `backend/app/repositories/dashboard.py` with record dataclasses and this public contract:

```python
@dataclass(frozen=True)
class DashboardCategoryRecord:
    category_id: UUID | None
    name: str
    color: str
    amount: Decimal
    percentage: Decimal


@dataclass(frozen=True)
class DashboardTrendRecord:
    period_start: date
    income: Decimal
    expense: Decimal


@dataclass(frozen=True)
class DashboardRecord:
    income: Decimal
    expense: Decimal
    categories: list[DashboardCategoryRecord]
    trend: list[DashboardTrendRecord]


class DashboardRepository(Protocol):
    def get(
        self,
        user_id: UUID,
        date_from: date,
        date_to: date,
        bucket: DashboardBucket,
    ) -> DashboardRecord: ...
```

Implement `InMemoryDashboardRepository` using `TransactionRepository.list()` and `CategoryRepository.get()`. Aggregate with `Decimal("0.00")`, quantize category percentages to `Decimal("0.01")` with `ROUND_HALF_UP`, bucket weeks by subtracting `record.date.weekday()` days, and bucket months with `record.date.replace(day=1)`. Sort categories by `(-amount, name.casefold())` and trend by `period_start`.

- [ ] **Step 5: Implement the service and stable labels**

Create `backend/app/services/dashboard.py` with:

```python
MONTH_LABELS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def select_bucket(date_from: date, date_to: date) -> DashboardBucket:
    inclusive_days = (date_to - date_from).days + 1
    if inclusive_days <= 31:
        return DashboardBucket.daily
    if inclusive_days <= 90:
        return DashboardBucket.weekly
    return DashboardBucket.monthly


def format_period_label(period_start: date, bucket: DashboardBucket) -> str:
    month = MONTH_LABELS[period_start.month - 1]
    return f"{period_start.day} {month}" if bucket is not DashboardBucket.monthly else f"{month} {period_start.year}"
```

`get_dashboard()` must reject `date_from > date_to`, call the repository with the selected bucket, compute `net = income - expense`, attach labels, and return `DashboardResponse` with aliased period fields.

- [ ] **Step 6: Wire the in-memory repository and route**

Add `build_dashboard_repository()` and singleton `dashboard_repository` in `backend/app/repositories/__init__.py`, constructing `InMemoryDashboardRepository(transaction_repository, category_repository)` in this task. Task 2 replaces the builder's database branch with `PostgresDashboardRepository` after that implementation has PostgreSQL tests. The dashboard repository owns no mutable state, so it does not need a `clear()` method; the existing transaction/category fixture cleanup is sufficient.

Create `backend/app/routers/dashboard.py`:

```python
@router.get("", response_model=DashboardResponse)
def dashboard(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    user_id: UUID = Depends(get_current_user_id),
) -> DashboardResponse:
    default_from, default_to = current_utc_month()
    resolved_from = date_from or default_from
    resolved_to = date_to or default_to
    if resolved_from > resolved_to:
        raise HTTPException(status_code=422, detail="from must be on or before to")
    return get_dashboard(repository, user_id, resolved_from, resolved_to)
```

Define `utc_today() -> date` as a small wrapper around `datetime.now(timezone.utc).date()` and use `calendar.monthrange()` in `current_utc_month()`. Include the router in `backend/app/main.py`.

- [ ] **Step 7: Run focused and full backend checks**

Run:

```bash
cd backend
PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest tests/test_dashboard.py -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest -q
```

Expected: dashboard tests pass, Ruff reports no errors, and the full in-memory suite passes with PostgreSQL tests skipped when `TEST_DATABASE_URL` is absent.

- [ ] **Step 8: Commit the backend contract**

```bash
git add backend/app backend/tests/test_dashboard.py
git commit -m "feat: add dashboard aggregation api"
```

---

### Task 2: PostgreSQL aggregation, index, and RLS integration tests

**Files:**
- Modify: `backend/app/repositories/dashboard.py`
- Modify: `backend/app/repositories/__init__.py`
- Modify: `backend/sql/init.sql`
- Create: `backend/sql/migrations/003_phase_3_dashboard_index.sql`
- Modify: `backend/tests/test_phase2_postgres.py`

**Interfaces:**
- Consumes: `DashboardRepository.get(...)` and response records from Task 1.
- Produces: `PostgresDashboardRepository(database_url: str)` with the same contract.
- Produces: idempotent `transactions_user_date_idx` on `transactions(user_id, date)`.

- [ ] **Step 1: Write failing PostgreSQL aggregate and index tests**

Extend `backend/tests/test_phase2_postgres.py` to construct `PostgresDashboardRepository(postgres_url)`, insert User A income/categorized expense/uncategorized expense plus a User B expense, and assert User A receives only their totals, category rows, and date buckets. Add:

```python
def test_dashboard_index_exists(postgres_url: str) -> None:
    with database_session(postgres_url, USER_A_ID) as connection:
        definition = connection.execute(
            "select indexdef from pg_indexes where schemaname = 'public' and indexname = 'transactions_user_date_idx'"
        ).fetchone()
    assert definition is not None
    assert "(user_id, date)" in definition["indexdef"]
```

- [ ] **Step 2: Run PostgreSQL tests and confirm failure**

Run:

```bash
docker compose up -d postgres
cd backend
TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@127.0.0.1:5432/finance_flow \
  PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest \
  tests/test_phase2_postgres.py -q
```

Expected: failure because `PostgresDashboardRepository` and/or `transactions_user_date_idx` are missing.

- [ ] **Step 3: Add the composite index to fresh and existing databases**

Add this statement to `backend/sql/init.sql` beside the other transaction indexes:

```sql
create index if not exists transactions_user_date_idx on transactions(user_id, date);
```

Create `backend/sql/migrations/003_phase_3_dashboard_index.sql`:

```sql
begin;

create index if not exists transactions_user_date_idx
  on transactions(user_id, date);

commit;
```

- [ ] **Step 4: Implement parameterized PostgreSQL aggregation**

Add `PostgresDashboardRepository` to `backend/app/repositories/dashboard.py`. Every query runs inside one `database_session(self.database_url, user_id)` block and includes:

```sql
where t.user_id = current_setting('app.user_id')::uuid
  and t.date >= %s
  and t.date <= %s
```

Use three focused queries in that transaction:

```sql
select
  coalesce(sum(amount) filter (where type = 'income'), 0.00)::numeric(12,2) as income,
  coalesce(sum(amount) filter (where type = 'expense'), 0.00)::numeric(12,2) as expense
from transactions t
where t.user_id = current_setting('app.user_id')::uuid
  and t.date between %s and %s;
```

```sql
with expense_totals as (
  select
    t.category_id,
    coalesce(c.name, 'Uncategorized') as name,
    coalesce(c.color, '#6B7280') as color,
    sum(t.amount)::numeric(12,2) as amount
  from transactions t
  left join categories c on c.id = t.category_id
  where t.user_id = current_setting('app.user_id')::uuid
    and t.type = 'expense'
    and t.date between %s and %s
  group by t.category_id, coalesce(c.name, 'Uncategorized'), coalesce(c.color, '#6B7280')
)
select category_id, name, color, amount,
       round(amount * 100 / sum(amount) over (), 2) as percentage
from expense_totals
order by amount desc, lower(name);
```

Build the trend expression only from the trusted enum, never request text:

```python
bucket_sql = {
    DashboardBucket.daily: "t.date",
    DashboardBucket.weekly: "date_trunc('week', t.date)::date",
    DashboardBucket.monthly: "date_trunc('month', t.date)::date",
}[bucket]
```

Then group by that expression and return numeric income/expense filters. Do not interpolate any user-controlled value into SQL.

Update `build_dashboard_repository()` in `backend/app/repositories/__init__.py` so a configured `DATABASE_URL` constructs `PostgresDashboardRepository(database_url)` and the no-database test path retains `InMemoryDashboardRepository`.

- [ ] **Step 5: Re-run PostgreSQL and full backend checks**

Run:

```bash
cd backend
TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@127.0.0.1:5432/finance_flow \
  PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
```

Expected: all tests pass including dashboard aggregation, index existence, and existing non-bypass RLS isolation tests.

- [ ] **Step 6: Commit PostgreSQL support**

```bash
git add backend/app/repositories/dashboard.py backend/app/repositories/__init__.py backend/sql backend/tests/test_phase2_postgres.py
git commit -m "feat: aggregate dashboard data in postgres"
```

---

### Task 3: Dashboard data client, periods, summary cards, and states

**Files:**
- Create: `frontend/lib/dashboard.ts`
- Create: `frontend/lib/dashboard.test.ts`
- Create: `frontend/app/dashboard-client.tsx`
- Create: `frontend/app/dashboard-client.test.tsx`
- Create: `frontend/test/setup.ts`
- Create: `frontend/vitest.config.ts`
- Modify: `frontend/app/page.tsx`
- Replace: `frontend/app/page.module.css`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `GET /dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD` from Task 1.
- Produces: `DashboardResponse`, `DashboardPeriodPreset`, `dateToInputValue()`, `thisMonthPeriod()`, `lastMonthPeriod()`, `dashboardQueryKey()`, and `getDashboard()`.
- Produces: authenticated `DashboardClient` with period controls, summary cards, loading, empty, and retry states.

- [ ] **Step 1: Install and configure the approved frontend test stack**

Run:

```bash
cd frontend
npm install --save-dev --save-exact \
  vitest@3.2.7 jsdom@26.1.0 \
  @testing-library/react@16.3.2 \
  @testing-library/dom@10.4.1 \
  @testing-library/jest-dom@7.0.0
```

Add `"test": "vitest run"` to `package.json`. Create `vitest.config.ts` with the `jsdom` environment, `test/setup.ts`, and an `@` alias resolved from `fileURLToPath(new URL(".", import.meta.url))`. In `test/setup.ts`, import `@testing-library/jest-dom/vitest` and call Testing Library `cleanup()` in `afterEach`.

Add `npm test` to the frontend CI job immediately after `npm ci` and before lint/build.

- [ ] **Step 2: Write failing calendar, query-key, and client-state tests**

Create `frontend/lib/dashboard.test.ts` with hand-derived literals proving:

```typescript
expect(dateToInputValue(new Date(2026, 6, 5))).toBe("2026-07-05");
expect(thisMonthPeriod(new Date(2026, 6, 15))).toEqual({ from: "2026-07-01", to: "2026-07-31" });
expect(lastMonthPeriod(new Date(2026, 0, 15))).toEqual({ from: "2025-12-01", to: "2025-12-31" });
expect(dashboardQueryKey("user-a", "2026-07-01", "2026-07-31")).toEqual([
  "dashboard", "user-a", "2026-07-01", "2026-07-31",
]);
```

Mock `requestJson` with its exact full call signature and assert `getDashboard("2026-07-01", "2026-07-31")` requests `/dashboard?from=2026-07-01&to=2026-07-31`.

Create `frontend/app/dashboard-client.test.tsx` with a real `QueryClientProvider`, a controlled `getDashboard` boundary response matching the full API shape, and narrow mocks only for `useAuth()` and `useRouter()`. Test the consumer-visible behavior: populated summary values, an empty response message, a rejected request with Retry, preset date changes, and Custom Apply disabled for missing/reversed dates.

Run:

```bash
cd frontend
npm test
```

Expected: tests fail because `dashboard.ts` and `DashboardClient` do not exist.

- [ ] **Step 3: Add typed API and calendar helpers**

Create `frontend/lib/dashboard.ts` with API types mirroring Pydantic strings exactly:

```typescript
export type DashboardBucket = "daily" | "weekly" | "monthly";

export interface DashboardResponse {
  period: { from: string; to: string; bucket: DashboardBucket };
  summary: { income: string; expense: string; net: string };
  categories: Array<{
    category_id: string | null;
    name: string;
    color: string;
    amount: string;
    percentage: string;
  }>;
  trend: Array<{
    period_start: string;
    label: string;
    income: string;
    expense: string;
  }>;
}
```

Implement local-calendar date formatting without `toISOString()`:

```typescript
export function dateToInputValue(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
```

`thisMonthPeriod(now)` returns local first/last month dates; `lastMonthPeriod(now)` uses `new Date(year, month - 1, 1)` and `new Date(year, month, 0)`. `dashboardQueryKey(userId, from, to)` returns `["dashboard", userId, from, to] as const`. `getDashboard()` URL-encodes both dates and calls `requestJson<DashboardResponse>()`.

- [ ] **Step 4: Build the client page with presets and auth behavior**

Create `frontend/app/dashboard-client.tsx` as a client component. Use `useAuth()`, default to `thisMonthPeriod(new Date())`, and keep draft custom dates separate from applied dates. Configure:

```typescript
const dashboardQuery = useQuery({
  queryKey: dashboardQueryKey(userId, period.from, period.to),
  queryFn: () => getDashboard(period.from, period.to),
  enabled: !configured || Boolean(session),
  placeholderData: (previousData) => previousData,
});
```

Redirect unauthenticated configured users to `/login` using the same visible sign-in card pattern as Transactions. Add This month, Last month, and Custom buttons. Custom Apply remains disabled when either date is blank or `from > to`.

- [ ] **Step 5: Render exact summary and state behavior**

Use `Intl.NumberFormat("sv-SE", { style: "currency", currency: "SEK" })` and convert API decimal strings only at the display boundary. Keep financial computation on the backend; the browser conversion is display-only and deterministic in tests.

Render three cards with semantic classes:

```tsx
<SummaryCard label="Income" value={formatCurrency(data.summary.income)} tone="income" />
<SummaryCard label="Expense" value={formatCurrency(data.summary.expense)} tone="expense" />
<SummaryCard label="Net" value={formatCurrency(data.summary.net)} tone={Number(data.summary.net) >= 0 ? "income" : "expense"} />
```

Render stable skeleton blocks while the first request loads, an error card with `dashboardQuery.refetch()` on Retry, and zero-value summary cards plus `No transactions in this period` when both chart arrays are empty.

- [ ] **Step 6: Replace the placeholder homepage and add responsive CSS**

Make `frontend/app/page.tsx` a thin server component:

```tsx
import { AppShellNav } from "@/components/layout/app-shell-nav";
import { DashboardClient } from "./dashboard-client";

export default function Home() {
  return (
    <AppShellNav>
      <DashboardClient />
    </AppShellNav>
  );
}
```

Replace `page.module.css` with dashboard-scoped layout classes. Use a three-column summary grid above a two-column chart grid, collapse both to one column below 760px, use only existing CSS color/radius tokens, and keep numbers `font-variant-numeric: tabular-nums`.

- [ ] **Step 7: Run frontend tests, lint, and build**

Run:

```bash
cd frontend
npm test
npm run lint
npm run build
```

Expected: tests pass and both lint/build exit 0; the dashboard page compiles without charts before Task 4.

- [ ] **Step 8: Commit the dashboard shell and test infrastructure**

```bash
git add frontend/app frontend/lib/dashboard.ts frontend/lib/dashboard.test.ts frontend/test frontend/vitest.config.ts frontend/package.json frontend/package-lock.json .github/workflows/ci.yml
git commit -m "feat: add dashboard periods and summary cards"
```

---

### Task 4: Recharts donut and income-versus-expense charts

**Files:**
- Create: `frontend/components/dashboard/category-donut.tsx`
- Create: `frontend/components/dashboard/category-donut.module.css`
- Create: `frontend/components/dashboard/category-donut.test.tsx`
- Create: `frontend/components/dashboard/cash-flow-chart.tsx`
- Create: `frontend/components/dashboard/cash-flow-chart.module.css`
- Create: `frontend/components/dashboard/cash-flow-chart.test.tsx`
- Modify: `frontend/app/dashboard-client.tsx`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

**Interfaces:**
- Consumes: `DashboardResponse["categories"]` and `DashboardResponse["trend"]` from Task 3.
- Produces: `<CategoryDonut categories={...} />` and `<CashFlowChart points={...} />`.

- [ ] **Step 1: Install compatible, exact chart dependencies**

Run:

```bash
cd frontend
npm install --save-exact recharts@3.10.1 react-is@19.2.4
```

Confirm `package.json` and `package-lock.json` contain exact versions without a caret.

- [ ] **Step 2: Write failing accessible-chart tests**

Create `category-donut.test.tsx` with two category fixtures and assert the rendered accessible summary exposes `Groceries`, text matching `/300,00/`, and `75.00%`. Create `cash-flow-chart.test.tsx` with two trend fixtures and assert an accessible summary exposes both period labels and both Income/Expense values. Assertions target text/list/table semantics owned by these components, not Recharts internals.

Run:

```bash
cd frontend
npm test -- components/dashboard
```

Expected: tests fail because both chart components do not exist.

- [ ] **Step 3: Implement the expense donut**

Create `CategoryDonut` with `ResponsiveContainer`, `PieChart`, `Pie`, `Cell`, `Tooltip`, and `Legend`. Convert `amount` and `percentage` strings to numbers only for Recharts rendering. Use each API category color, `dataKey="amount"`, `nameKey="name"`, an inner radius, and tooltip currency formatting. Include an adjacent semantic list showing category name, formatted amount, and percentage so the chart remains understandable without color.

- [ ] **Step 4: Implement the grouped cash-flow chart**

Create `CashFlowChart` with `ResponsiveContainer`, `BarChart`, `CartesianGrid`, `XAxis`, `YAxis`, `Tooltip`, `Legend`, and two `Bar` components. Map string values to numeric `income`/`expense` fields for Recharts. Use `var(--state-success)` for Income and `var(--state-error)` for Expense, show API labels on the x-axis, and format tooltip/y-axis values as SEK. Include a visually-hidden semantic table with Period, Income, and Expense columns so the chart data is available without SVG or color.

- [ ] **Step 5: Wire charts and accessible empty states**

In `DashboardClient`, render chart cards only when their respective arrays contain data. Otherwise render `No expense categories in this period` and `No cash-flow activity in this period`. Add `aria-labelledby` relationships between chart headings and their containers; do not rely on tooltip hover as the only readable representation.

- [ ] **Step 6: Verify frontend tests, lint, and production build**

Run:

```bash
cd frontend
npm test
npm run lint
npm run build
```

Expected: chart and client tests pass; lint and build exit 0 with Recharts bundled successfully for Next.js 16/React 19.

- [ ] **Step 7: Commit chart implementation**

```bash
git add frontend/components/dashboard frontend/app/dashboard-client.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: visualize dashboard insights"
```

---

### Task 5: Supabase deployment, documentation, and end-to-end verification

**Files:**
- Modify: `context/progress-tracker.md`
- Create: `context/feature-specs/05-insights-dashboard.md`

**Interfaces:**
- Consumes: completed backend, index migration, and frontend dashboard.
- Produces: deployed Supabase index, recorded Phase 3 contract, and fresh verification evidence.

- [ ] **Step 1: Apply the idempotent index migration to Supabase**

Using the configured `DATABASE_URL` from `/Users/gauravsharma/Personal/finance-tracker/backend/.env.local`, execute only `backend/sql/migrations/003_phase_3_dashboard_index.sql`. Do not print the URL or password. Verify with:

```sql
select indexname, indexdef
from pg_indexes
where schemaname = 'public'
  and indexname = 'transactions_user_date_idx';
```

Expected: one index on `(user_id, date)`.

- [ ] **Step 2: Run complete backend verification with PostgreSQL**

Run:

```bash
docker compose up -d postgres
cd backend
TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@127.0.0.1:5432/finance_flow \
  PYTHONPATH=. /Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/pytest -q
/Users/gauravsharma/Personal/finance-tracker/backend/.venv/bin/ruff check app tests
```

Record exact pass/skip/warning counts.

- [ ] **Step 3: Run complete frontend verification**

Run:

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
```

Record exact frontend test counts and exit status for dependency installation, lint, and build.

- [ ] **Step 4: Perform authenticated dashboard smoke coverage**

Start FastAPI with the configured Supabase environment and Next.js with `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8100`. In a signed-in browser verify:

1. `/` loads This month and shows summary cards.
2. Last month changes the API dates and refreshes all panels.
3. Custom rejects a reversed range and applies a valid range.
4. The known `Test purchase` expense contributes to the correct summary/category/trend period.
5. An empty range shows zero cards and both empty messages.
6. Stopping the backend shows the Retry state; restarting it and clicking Retry restores data.
7. Signing out redirects to login; signing in as another user does not display the first user's cached dashboard.

- [ ] **Step 5: Record the Phase 3 contract and progress**

Create `context/feature-specs/05-insights-dashboard.md` summarizing the final endpoint, response, bucket rules, UI states, tests, and exclusions from the approved design. Update `context/progress-tracker.md` to Phase 3, list completed dashboard work, and retain any smoke-test limitation as an explicit in-progress item rather than claiming completion.

- [ ] **Step 6: Run final diff and repository checks**

Run:

```bash
git diff --check
git status --short
git log --oneline --decorate -8
```

Confirm only Phase 3 files are changed and the Phase 2 worktree remains untouched.

- [ ] **Step 7: Commit verification documentation**

```bash
git add context/feature-specs/05-insights-dashboard.md context/progress-tracker.md
git commit -m "docs: record phase 3 dashboard status"
```
