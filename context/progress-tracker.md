# Progress Tracker

Update this file after every meaningful implementation change.

## Current Phase

- Phase 4 — Smart Categorization. Implementation, remote schema deployment,
  rule-only smoke, and automated verification are complete; authenticated
  browser smoke remains unavailable.

## Current Goal

- Preserve the explicit Phase 2–4 authenticated browser verification gaps,
  then begin Phase 5 deployment planning.

## Completed

- Repo scaffold exists with `frontend/` and `backend/`.
- Backend FastAPI skeleton exists with `/health` and tests.
- Frontend Next.js skeleton exists and is cleaned up for Finance Flow.
- Docker Compose and CI workflow are present.
- Root context files are now the single source of truth.
- Frontend foundation spec exists at `context/feature-specs/01-foundation.md`.
- Frontend shell/navigation spec exists at `context/feature-specs/02-shell-navigation.md`.
- Transaction CRUD spec exists at `context/feature-specs/03-transactions-crud.md`.
- Frontend foundation primitives and shell are implemented.
- Frontend build and lint pass.
- Frontend app shell / navbar implemented from
  `context/feature-specs/02-shell-navigation.md`.
- Transaction CRUD backend contract now matches the UUID-based spec.
- Transaction CRUD frontend now uses TanStack Query, filters, and the
  exact `category_id` / `account_id` field names.
- Frontend Supabase auth provider, login page, and sign-out controls are
  implemented.
- Backend pytest passes for create, list, delete, and validation.
- Backend auth now verifies Supabase access tokens with JWKS for the
  current P-256 signing keys, with HS256 fallback for legacy/local cases.
- Frontend lint and production build pass after the transaction CRUD work.
- Postgres-backed persistence was smoke-tested in the Docker Compose
  network with real create/read/delete behavior.
- Root context remains the single source of truth for feature specs and
  progress tracking.
- Phase 2 data model, stable global defaults, forced RLS policies, reference
  ownership trigger, and additive migration are implemented.
- Category API supports authenticated create/list/update/delete, immutable
  global defaults, validation, duplicate detection, and per-user isolation.
- Account API supports authenticated create/list/update/delete, normalized
  names, duplicate detection, sorted lists, and per-user isolation.
- Transaction writes validate category/account ownership, list filtering
  supports both resources, and resource deletion preserves transactions.
- PostgreSQL 16 CI coverage exercises RLS, cross-user isolation, reference
  validation, and delete-to-null behavior with a non-bypass application role.
- Categories and Accounts pages support authenticated create, list, edit, and
  delete flows; global categories are read-only and custom category colors are
  assigned automatically from the approved palette.
- Local preview origins on ports 3000 and 3100 are covered by CORS regression
  tests so resource names load correctly during review.
- Transaction creation and editing now use named category and account selectors.
  The transaction list renders resource names with safe missing-reference
  fallbacks, and its filters cover both category and account. All transaction,
  category, and account query caches are scoped by authenticated user ID.
- The Phase 3 dashboard shell now includes an authenticated period selector,
  typed FastAPI dashboard client, summary cards, and loading, empty, and retry
  states. Chart rendering remains the next dashboard unit.
- The Phase 3 dashboard now visualizes expense categories with a Recharts
  donut and cash flow with grouped income and expense bars. Both charts expose
  semantic text summaries for use without colour or SVG, and each has an
  explicit empty state.
- The Phase 3 `GET /dashboard` contract now supplies authenticated,
  user-scoped selected-period income, expense, net, expense-category, and
  trend aggregates. It defaults to the current UTC month and selects daily,
  weekly, or monthly buckets from the inclusive range length.
- The idempotent `transactions_user_date_idx` migration was applied to the
  configured remote Supabase database and verified as a valid `(user_id, date)`
  index. No remote application data was modified by this deployment step.
- Phase 3 automated verification on 2026-07-31 passed: backend `35 passed,
  1 warning` against isolated PostgreSQL on port 5433; backend Ruff clean;
  frontend `npm ci`, 14 Vitest tests, lint, and production build all passed.
- Dashboard client query keys include both authenticated user ID and applied
  dates, preventing a prior user's dashboard cache from being displayed while
  another user's request is pending.
- The Phase 4 Rules page now provides authenticated, user-scoped rule CRUD
  through FastAPI, including category selection, enable/disable controls, and
  user-isolated TanStack Query caches.
- The Phase 4 Transactions page now shows pending, failed, rule, and OpenAI
  categorization states; polls only while work is pending; supports retry; and
  offers explicit, editable rule creation after a saved automatic correction.
- Phase 4 categorization defaults to deterministic `rules` mode. An ambient
  OpenAI key is ignored, unmatched descriptions finish `not_requested`, and no
  OpenAI client or request is created. OpenAI remains available only through
  explicit `CATEGORIZATION_PROVIDER=openai`; unsupported modes fail startup.
- Migration `004_phase_4_smart_categorization.sql` was applied by itself to
  the configured remote Supabase database. Read-only verification confirmed
  the rules table, all columns and constraints, forced RLS and own-rows policy,
  ownership trigger, unique keyword index, zero incomplete backfill rows, and
  three correctly backfilled manual transactions.
- The Phase 4 rule-only smoke passed with an ambient OpenAI key present: a
  `spotify` rule categorized its match, an unmatched description finished
  `not_requested`, and the configured provider remained absent.
- Phase 4 automated verification on 2026-08-04 passed: backend `89 passed,
  1 warning` against isolated PostgreSQL on port 5433; backend Ruff and lock
  checks clean; frontend `47 passed` across 8 files, lint, and production build
  all passed.

## In Progress

- Full authenticated Phase 2 UI smoke test, including multi-user isolation.
- Full authenticated Phase 3 dashboard smoke test: selected presets and custom
  ranges, known `Test purchase` aggregation, empty-range states, Retry after a
  backend restart, sign-out redirect, and multi-user cache isolation. This
  remains unverified because no controllable signed-in browser was available
  in the 2026-07-31 verification session.
- Full authenticated Phase 4 smoke test: manual bypass, rule categorization and
  badge, rules-mode unmatched behavior, late manual override protection,
  correction dismissal, correction-to-rule creation/editing, and real User A
  to User B data/cache isolation. The 2026-08-04 browser runtime exposed no
  controllable browser, so none of these are claimed as live observations.

## Next Up

- Complete the authenticated Phase 2, Phase 3, and Phase 4 multi-user UI smoke
  tests when a controllable signed-in browser is available.
- Begin Phase 5 deployment planning and select the backend host.

## Open Questions

- **Visual design is not specified in the source spec.** `ui-context.md`
  currently uses proposed default tokens (light theme). Confirm or replace.
- **Backend host for deployment (Phase 5):** Render vs. Fly.io vs. Railway
  — decide before Phase 5. All free tiers may cold-start after idle.

## Architecture Decisions

- **FastAPI sits between the frontend and Supabase** rather than calling
  Supabase directly from the browser — chosen for clean separation of
  concerns and as a stronger fintech-portfolio signal.
- **Money is `numeric(12,2)`, never float** — floats lose precision on
  money, a red flag in a fintech project. Amount stored positive; `type`
  gives direction.
- **User id always comes from the verified Supabase JWT (`sub` claim)** —
  never trusted from the request body.
- **Row Level Security enabled on all tables** — defence in depth matching
  the API's per-user scoping.
- **Categorization runs as a FastAPI background task** — creating a
  transaction stays fast; the category fills in shortly after.
- **Rule-only categorization is the default** — user rules require no paid
  provider. OpenAI is retained as a server-side future option and requires the
  explicit `CATEGORIZATION_PROVIDER=openai` opt-in.
- **CSS Modules, no component library** — scoped styles per component;
  charts via Recharts; data fetching via TanStack Query.

## Session Notes

- Transaction selector/filter implementation verification passed on 2026-07-29:
  frontend TypeScript, lint, and production build passed; backend Ruff passed;
  backend pytest reported 19 passed and 1 skipped with the existing Starlette
  `on_event` deprecation warning.
- The local backend and frontend started successfully at
  `http://127.0.0.1:8100` and `http://127.0.0.1:3100`, respectively. The
  authenticated click-through scenarios were not observed because no
  controllable browser was attached to this Codex session. Multi-user UI
  isolation therefore remains an explicit verification gap.
- Phase 3 verification on 2026-07-31 used the existing isolated Docker
  PostgreSQL container at `127.0.0.1:5433`; the user-owned PostgreSQL listener
  on port 5432 was not stopped, replaced, or rebound. A browser connection was
  unavailable, so no authenticated click-through claims are made.
- Phase 4 release verification on 2026-08-04 reused the same isolated
  PostgreSQL test port and the configured remote Supabase backend. A live
  OpenAI smoke returned `429 credit_balance_exhausted`; the user then approved
  rule-only default behavior so paid-provider access is no longer a Phase 4
  requirement. Browser discovery returned no available browser types, so the
  Phase 4 click-through scenarios remain explicitly unverified.
- Two context PDFs are the authoritative source: the complete project
  guide and the detailed all-phases spec. Phases run 0 → 6; value
  concentrates in Phases 1, 3, and 5. Target: ~4–6 weeks part-time to a
  strong, deployed Phase 5. Phases 4 and 6 are the differentiators once
  the core is solid.
