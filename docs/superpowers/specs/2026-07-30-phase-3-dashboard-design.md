# Phase 3 Insights Dashboard Design

## Goal

Replace the placeholder homepage with an authenticated dashboard that tells
the signed-in user's money story for a selected period. The dashboard shows
income, expense, net, expense share by category, and income versus expense
over time.

## Scope

Phase 3 includes:

- Summary cards for income, expense, and net.
- An expense-by-category donut chart.
- An income-versus-expense grouped bar chart.
- This month, last month, and custom date-range controls.
- Automatic daily, weekly, or monthly time grouping.
- Authenticated, user-isolated aggregation through FastAPI.

The dashboard combines transactions from all accounts. Account filtering,
budgets, forecasting, smart categorization, and comparison percentages are
outside this phase.

## API

Add one authenticated endpoint:

```text
GET /dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD
```

The verified Supabase JWT subject is the only source of the user ID. Both
dates are inclusive. Missing dates default to the current UTC calendar month.
Malformed dates or a `from` date later than `to` return `422`.

The response contains:

```json
{
  "period": {
    "from": "2026-07-01",
    "to": "2026-07-31",
    "bucket": "daily"
  },
  "summary": {
    "income": "2500.00",
    "expense": "900.00",
    "net": "1600.00"
  },
  "categories": [
    {
      "category_id": "00000000-0000-4000-8000-000000000002",
      "name": "Groceries",
      "color": "#16A34A",
      "amount": "300.00",
      "percentage": "33.33"
    }
  ],
  "trend": [
    {
      "period_start": "2026-07-01",
      "label": "1 Jul",
      "income": "2500.00",
      "expense": "100.00"
    }
  ]
}
```

Money and percentages use PostgreSQL numeric/Python Decimal values, never
float calculations. JSON preserves exact decimal values as strings.
Net is calculated as income minus expense. Each category percentage is its
expense amount divided by total expense for the period; when total expense is
zero, the category array is empty.

Only expenses contribute to the category breakdown. Transactions without a
category are grouped under `Uncategorized` with a neutral color. Category
rows are ordered by amount descending with a stable name tie-breaker.

## Time grouping

The backend selects the bucket from the inclusive period length:

- 1–31 days: daily
- 32–90 days: weekly
- 91 days or more: monthly

Weeks start on Monday and months use calendar-month boundaries. All grouping
uses the transaction `date` value, so timezone conversion is not involved.
The trend includes only buckets containing transactions. Income and expense
values within a returned bucket default independently to zero.

## Backend structure

Create a dedicated dashboard repository protocol with in-memory and
PostgreSQL implementations, following the existing repository wiring pattern.
The PostgreSQL implementation performs server-side aggregation inside the
existing user-scoped database session so RLS and `app.user_id` remain in
force. It may issue focused summary, category, and trend queries inside one
request; the frontend still receives one consistent endpoint response.

The router owns query validation and period defaults. Repository records are
converted to explicit Pydantic response schemas. Empty periods return zero
summary values and empty category/trend arrays.

## Frontend

The existing `/` route becomes the dashboard and remains inside
`AppShellNav`. It requires the existing auth session and sends all requests
through FastAPI.

The page contains:

1. A heading and period controls.
2. Three summary cards: Income, Expense, and Net.
3. A responsive expense-by-category donut chart.
4. A responsive grouped bar chart for income and expense over time.

Preset controls calculate calendar boundaries in the browser:

- This month: first through last day of the current month.
- Last month: first through last day of the previous month.
- Custom: start and end date fields plus Apply.

Preset and custom dates use the browser's local calendar. Apply is disabled
until both custom dates are present and the start is not later than the end.
The TanStack Query key includes the authenticated user ID and both resolved
dates. TanStack Query's `placeholderData` retains the previous period while
the new period loads. Signing out or changing users cannot reuse another
user's dashboard cache.

Add Recharts as the chart dependency. Charts use semantic income/expense
tokens, category colors supplied by the API, responsive containers, visible
legends/tooltips, and text summaries or labels so meaning is not conveyed by
color alone.

Loading renders stable card and chart placeholders. API failures render an
error message with Retry. Empty periods show zero summary values and
`No transactions in this period` instead of empty chart frames. On narrow
screens, cards and charts stack vertically.

## Testing

Backend tests cover:

- Income, expense, and net totals.
- Expense-only category aggregation and percentages.
- Uncategorized expenses.
- Daily, weekly, and monthly bucket thresholds.
- Empty periods.
- Invalid and reversed date ranges.
- Per-user isolation.

PostgreSQL integration tests verify server-side aggregation and per-user
isolation under the existing non-bypass application role. Existing backend
Ruff and pytest must pass.

Frontend verification consists of TypeScript compilation, ESLint, production
build, and an authenticated smoke test for both presets and a custom range.
The smoke test checks loading, populated, empty, and error/retry states.

## Completion criteria

Phase 3 is complete when a signed-in user can open `/`, select each supported
period, and see correct user-isolated summary and chart data; backend tests,
Ruff, frontend lint, and frontend build pass; and the authenticated dashboard
smoke test is recorded.
