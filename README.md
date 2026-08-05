# Finance Tracker

Finance Tracker is a multi-user personal-finance app built with Next.js,
FastAPI, PostgreSQL/Supabase, and deterministic smart categorization. It turns
transactions into period summaries, category breakdowns, cash-flow trends,
and user-managed automation rules.

## Implemented features

- transaction, category, and account CRUD with ownership validation;
- Supabase Auth JWT verification and forced PostgreSQL RLS;
- dashboard income, expense, net, category, and trend aggregates;
- keyword-to-category rules with a user-scoped Rules manager;
- background transaction categorization with manual-edit race protection;
- accessible Auto/rule and optional Auto/OpenAI states;
- user-scoped frontend caches and session-change state reset.

Smart categorization is rule-only by default and requires no paid provider.
OpenAI support remains available as an explicit, optional server-side mode.

## Stack

- Next.js, TypeScript, CSS Modules, TanStack Query, and Recharts
- FastAPI, Pydantic, psycopg, and PostgreSQL 16
- Supabase Auth and hosted PostgreSQL
- Pytest, Ruff, Vitest, ESLint, and Docker Compose

## Project layout

```text
frontend/                  Next.js UI and typed FastAPI clients
backend/app/               FastAPI routes, repositories, and services
backend/sql/               local schema and additive remote migrations
backend/tests/             unit, API, PostgreSQL, RLS, and concurrency tests
context/                   architecture, product, UI, and feature specs
docker-compose.yml         local PostgreSQL/backend/frontend services
```

## Configuration

Copy `.env.example` to a local untracked environment file and replace only the
values needed for the selected setup. Never expose server-side values through a
`NEXT_PUBLIC_` variable.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Backend PostgreSQL connection string. |
| `SUPABASE_URL` | Supabase project URL used for JWT issuer/JWKS verification. |
| `SUPABASE_JWT_SECRET` | Optional legacy/local HS256 verification fallback. |
| `CATEGORIZATION_PROVIDER` | `rules` by default; set `openai` only for explicit provider opt-in. |
| `OPENAI_API_KEY` | Optional server-side key used only in OpenAI mode. |
| `OPENAI_CATEGORIZATION_MODEL` | Optional OpenAI model override. |
| `OPENAI_CATEGORIZATION_TIMEOUT_SECONDS` | Optional provider timeout; defaults to 8 seconds. |
| `NEXT_PUBLIC_API_BASE_URL` | Browser-visible FastAPI base URL. |
| `NEXT_PUBLIC_SUPABASE_URL` | Browser-visible Supabase Auth URL. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Browser-safe Supabase publishable/anon key. Never use a service key. |
| `NEXT_PUBLIC_DEV_AUTH_TOKEN` | Optional local-only token for the unconfigured development mode. |

`CATEGORIZATION_PROVIDER=rules` is the safe default even when
`OPENAI_API_KEY` happens to be present. In this mode the application creates no
OpenAI provider or client. An unmatched description becomes uncategorized with
status `not_requested`.

With `CATEGORIZATION_PROVIDER=openai`, rules still run first. Only unmatched
descriptions reach the provider, and the request contains description,
transaction type, and allowed category IDs/names only. Provider failures use
the existing failed/Retry state. Responses requests set `store=false`, which
disables Responses API application-state storage for these calls. This does
not disable ordinary OpenAI abuse-monitoring retention and is not a claim of
Zero Data Retention; those controls require separate OpenAI approval and
configuration. Unsupported provider-mode values stop startup with a
configuration error. See [OpenAI API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint).

## Local setup

Requirements: Python 3.12+, `uv`, Node.js/npm, and Docker.

1. Create local environment files from `.env.example`. For real Supabase Auth,
   set `SUPABASE_URL` for FastAPI and the two `NEXT_PUBLIC_SUPABASE_*` values in
   `frontend/.env.local`.
2. Start the local database:

   ```bash
   docker compose up -d postgres
   ```

3. Install and run the backend:

   ```bash
   cd backend
   uv sync
   CATEGORIZATION_PROVIDER=rules uv run uvicorn app.main:app --reload
   ```

4. Install and run the frontend in a second terminal:

   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

The frontend opens at `http://localhost:3000`; FastAPI listens at
`http://localhost:8000`. The Docker PostgreSQL service initializes the current
schema from `backend/sql/init.sql`.

To run the complete stack through Docker after configuring the root `.env`:

```bash
docker compose up --build
```

## Verification

Backend, using a disposable PostgreSQL service rather than a user database:

```bash
cd backend
TEST_DATABASE_URL=postgresql://finance_flow:finance_flow@127.0.0.1:5433/finance_flow \
  PYTHONPATH=. pytest -q
ruff check app tests
uv lock --check
```

Frontend:

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
```

The latest Phase 4 release evidence is recorded in
`context/feature-specs/06-smart-categorization.md` and
`context/progress-tracker.md`.

## Current status

Phases 1–4 are implemented: transaction management, categories/accounts,
dashboard insights, and smart categorization. Deployment and Open Banking are
future phases. Authenticated browser smoke gaps are kept explicit in the
progress tracker rather than inferred from automated coverage.
