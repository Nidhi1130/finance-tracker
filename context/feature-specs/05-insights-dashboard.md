# Phase 3 — Insights Dashboard

## Scope

The authenticated dashboard converts a user's transactions into a selected
period's income, expense, net, expense-category breakdown, and cash-flow
trend. The Next.js client calls FastAPI only; FastAPI derives the user from
the verified Supabase JWT and reads PostgreSQL under the existing RLS model.

## API contract

`GET /dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD` requires authentication. Both
query parameters are optional; omitted values default to the current UTC
calendar month. `from` later than `to`, and malformed dates, return `422`.

```json
{
  "period": { "from": "2026-07-01", "to": "2026-07-31", "bucket": "daily" },
  "summary": { "income": "1200.00", "expense": "400.00", "net": "800.00" },
  "categories": [
    {
      "category_id": "uuid-or-null",
      "name": "Groceries",
      "color": "#16A34A",
      "amount": "300.00",
      "percentage": "75.00"
    }
  ],
  "trend": [
    {
      "period_start": "2026-07-01",
      "label": "1 Jul",
      "income": "1200.00",
      "expense": "0.00"
    }
  ]
}
```

Amounts and percentages preserve `numeric` precision and are serialized as
decimal strings. The response is scoped to the authenticated user and uses
inclusive `from`/`to` boundaries.

## Aggregation rules

- A range of 31 inclusive days or fewer is bucketed daily; 32–90 days is
  bucketed weekly; longer ranges are bucketed monthly.
- Weekly buckets begin on Monday; monthly buckets begin on the first day of
  the month. Trend rows contain only periods with transaction activity.
- Summary income and expense sum positive transaction amounts by `type`; net
  is income minus expense.
- Categories contain expense transactions only. Missing/deleted categories
  are grouped as `Uncategorized` with `#6B7280`. Categories are ordered by
  descending amount, then case-insensitive name; zero-total categories are
  omitted. Percentages are each category's share of total expense, rounded to
  two decimal places with half-up rounding.
- `transactions_user_date_idx` indexes `(user_id, date)` for the scoped date
  aggregations. The idempotent migration is deployed to the configured remote
  Supabase database and was verified on 2026-07-31.

## Dashboard UI

- `/` presents This month, Last month, and Custom period controls. Presets
  change the requested dates; Custom keeps Apply disabled until both dates are
  present and ordered.
- Three SEK-formatted summary cards show income, expense, and net. Expense
  categories use a Recharts donut with a semantic text list; cash flow uses
  grouped income/expense bars with a semantic table.
- The client shows skeleton cards while first loading, an error plus Retry on
  request failure, and zero summary cards with explicit category, cash-flow,
  and transaction empty messages for an empty range.
- Dashboard query keys include authenticated user ID and the applied dates so
  switching users cannot reuse the prior user's cached dashboard data.
- When Supabase Auth is configured and no session exists, the dashboard shows
  an authentication-required state that sends the user to login.

## Verification evidence — 2026-07-31

- Remote migration: only `backend/sql/migrations/003_phase_3_dashboard_index.sql`
  was applied. The exact `pg_indexes` query returned one valid
  `transactions_user_date_idx` on `public.transactions (user_id, date)`.
- Backend against isolated Docker PostgreSQL on `127.0.0.1:5433`: `35 passed,
  1 warning` from `pytest -q`; `ruff check app tests` passed. The warning is
  the existing Starlette TestClient/httpx deprecation.
- Frontend: `npm ci` completed; `npm test` reported `4 passed` files and
  `14 passed` tests; `npm run lint` and `npm run build` passed. Installation
  reported one deprecated package and 12 high-severity audit findings; neither
  was changed as part of this phase.

## Explicit exclusions / follow-up

- A controllable signed-in browser was unavailable in this session. The
  required authenticated UI smoke scenarios remain unverified: live preset and
  custom requests, known `Test purchase` aggregation, live empty range,
  backend-stop/Retry recovery, sign-out redirect, and real multi-user cache
  isolation.
- No frontend component reads Supabase or PostgreSQL directly, and this phase
  adds no AI categorization, bank import, deployment, or data mutation beyond
  the approved index migration.
