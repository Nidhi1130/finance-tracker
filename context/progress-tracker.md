# Progress Tracker

Update this file after every meaningful implementation change.

## Current Phase

- Phase 1 — Core finance workflows. Complete.

## Current Goal

- Phase 1 is complete. Next up is the categories/accounts expansion and
  the deeper auth flow.

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

## In Progress

- None.

## Next Up

- Start the next phase slice: categories, accounts, and auth flows.
- Then tighten the root README and repo metadata to match the current
  Finance Flow branding and project summary.

## Open Questions

- **Visual design is not specified in the source spec.** `ui-context.md`
  currently uses proposed default tokens (light theme). Confirm or replace.
- **Backend host for deployment (Phase 5):** Render vs. Fly.io vs. Railway
  — decide before Phase 5. All free tiers may cold-start after idle.
- **LLM provider (Phase 4):** Anthropic vs. OpenAI. Decide before Phase 4;
  keep rule-based categorization primary to keep cost near zero.
- **Accounts entity timing:** the current agenda keeps accounts optional
  in this slice. Create the table shape now, but defer full accounts UI
  and CRUD until a later phase.

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

- Two context PDFs are the authoritative source: the complete project
  guide and the detailed all-phases spec. Phases run 0 → 6; value
  concentrates in Phases 1, 3, and 5. Target: ~4–6 weeks part-time to a
  strong, deployed Phase 5. Phases 4 and 6 are the differentiators once
  the core is solid.
