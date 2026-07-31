# Progress Tracker

Update this file after every meaningful implementation change.

## Current Phase

- Phase 2 — Categories & Accounts. In progress; transaction UI verification remains.

## Current Goal

- Deliver the locked Phase 2 data model, authenticated category/account CRUD,
  transaction selectors and filters, isolation tests, and UI smoke coverage.

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

## In Progress

- Full authenticated Phase 2 UI smoke test, including multi-user isolation.

## Next Up

- Complete the authenticated multi-user UI smoke test.
- Then tighten the root README and repo metadata to match Finance Flow.

## Open Questions

- **Visual design is not specified in the source spec.** `ui-context.md`
  currently uses proposed default tokens (light theme). Confirm or replace.
- **Backend host for deployment (Phase 5):** Render vs. Fly.io vs. Railway
  — decide before Phase 5. All free tiers may cold-start after idle.
- **LLM provider (Phase 4):** Anthropic vs. OpenAI. Decide before Phase 4;
  keep rule-based categorization primary to keep cost near zero.

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
- Two context PDFs are the authoritative source: the complete project
  guide and the detailed all-phases spec. Phases run 0 → 6; value
  concentrates in Phases 1, 3, and 5. Target: ~4–6 weeks part-time to a
  strong, deployed Phase 5. Phases 4 and 6 are the differentiators once
  the core is solid.
