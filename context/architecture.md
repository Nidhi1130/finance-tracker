# Architecture Context

## Stack

| Layer          | Technology            | Role                                              |
| -------------- | --------------------- | ------------------------------------------------- |
| Frontend       | Next.js + TypeScript  | UI, file-based routing, SSR, calls FastAPI only   |
| Styling        | CSS Modules           | Scoped per-component styles, no class collisions  |
| Data fetching  | TanStack Query        | Client-side fetching, caching, invalidation       |
| Charts         | Recharts              | Dashboard visualizations (donut, line/bar)        |
| API            | FastAPI + Pydantic    | Business logic, validation, the only DB client    |
| Auth           | Supabase Auth         | Signup/login, issues the JWT the API verifies     |
| Database       | Supabase (PostgreSQL) | Storage, Row Level Security                        |
| Local dev      | Docker Compose        | Backend + local Postgres via one command          |
| CI             | GitHub Actions        | Lint + tests on every push                        |

## System Boundaries

- `frontend/` — Next.js + TypeScript app. Owns all UI, pages, forms,
  charts, and client-side state. Talks **only** to FastAPI; never touches
  the database directly.
- `backend/` — FastAPI + Pydantic app. Owns validation, business logic,
  aggregation, and categorization. The **only** component that talks to
  Postgres.
- `backend/app/routers/` (or `api/`) — HTTP endpoints; thin, focused on
  parsing input, enforcing auth, and shaping responses.
- `backend/app/services/` — business logic (aggregation queries,
  categorization rules + LLM fallback, bank import).
- Supabase — hosted Postgres + Auth. Owns the `auth.users` table and JWT
  issuance; enforces Row Level Security.

## Storage Model

- **Database (Postgres / Supabase)**: all application data lives here —
  it is a relational, metadata-only app. Tables: `categories`,
  `accounts`, `transactions`, `categorization_rules` (Phase 4),
  `bank_connections` (Phase 6). Ownership is expressed via `user_id`
  referencing `auth.users(id)`.
- **No blob / file storage**: there is no large binary content in this
  project. If that ever changes, add it here as an explicit decision.
- **Money**: stored as `numeric(12,2)`, never float. Amounts are stored
  positive; `type` (`income` / `expense`) gives direction.

## Auth and Access Model

- Every user signs in via Supabase Auth (email/password or magic link).
- The frontend sends the Supabase JWT with each request. FastAPI has a
  dependency that verifies the JWT (signature + expiry) and extracts the
  user id from the `sub` claim.
- The authenticated user id **always** comes from the verified JWT, never
  from the request body or query params.
- Every query is scoped to the current user's id.
- Row Level Security is enabled on all tables as defence in depth, so a
  user can only read/write their own rows. Global categories
  (`user_id is null`) stay readable by everyone.

## Invariants

1. The frontend never talks to the database directly. It only calls
   FastAPI, and FastAPI is the only thing that talks to Postgres.
2. Money is stored as `numeric(12,2)`, never float. Amounts are stored
   positive; `type` gives direction.
3. The authenticated user id comes from the verified JWT `sub` claim —
   never from the request body, never trusted from the client.
4. Every DB query is scoped to the current user; RLS enforces the same
   scoping at the database layer even if application code slips.
5. Long-running work (LLM categorization, bank import) runs as a
   background task. Request handlers stay fast and do not block on it.
6. Each phase ships as a working, demoable app. A phase is not started
   until the previous phase's "done when" criteria are met.
