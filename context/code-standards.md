# Code Standards

## General

- Keep modules small and single-purpose; one responsibility per file.
- Fix root causes, do not layer workarounds.
- Do not mix unrelated concerns in one component, route, or service.
- Commit in small, well-described increments — not one giant "final
  commit." Use branches + pull requests even when working solo.

## TypeScript (frontend)

- Strict mode is required throughout the frontend.
- Avoid `any` — use explicit interfaces or narrowly scoped types. Types
  for API responses should mirror the FastAPI/Pydantic output schemas.
- Validate or narrow unknown external input at boundaries before trusting
  it (e.g. API responses, URL/query params).

## Next.js (frontend)

- Default to server components; add `use client` only when browser
  interactivity requires it (forms, charts, TanStack Query hooks).
- Use file-based routing; keep pages thin and push logic into components
  or hooks.
- All data fetching goes through TanStack Query — no ad-hoc `fetch` calls
  scattered through components. Centralize the API base URL and auth
  header.
- The frontend calls FastAPI only. Never call Supabase or Postgres
  directly from the frontend.

## Python / FastAPI (backend)

- Use Pydantic for all request and response models. Keep input and output
  schemas separate (e.g. `TransactionCreate` vs. `TransactionOut`) — this
  also keeps the auto-generated `/docs` readable.
- Ruff is the linter/formatter; keep the backend Ruff-clean.
- Route handlers stay thin: parse input, enforce auth, call a service,
  shape the response. Business logic lives in `services/`.

## Styling

- Use CSS Modules — one scoped `*.module.css` file per component. Import
  it and use `className={styles.myClass}`; never rely on global class
  names that can collide.
- Use CSS custom property tokens for colors, spacing, and radius — no
  hardcoded hex values in component styles. See `ui-context.md`.

## API Routes

- Validate and parse request input (via Pydantic) before any logic runs.
- Enforce auth on every route: verify the Supabase JWT and derive the
  user id from the `sub` claim before any read or mutation.
- Scope every query to the authenticated user id. Never accept `user_id`
  from the request body.
- Return consistent, predictable response shapes and correct status codes
  (201 on create, 204 on delete, etc.).
- Money is `numeric` end to end — validate `amount > 0` at the schema
  boundary; `type` carries direction.

## Data and Storage

- All metadata belongs in Postgres (via Supabase).
- Money columns are `numeric(12,2)`, never float. Store amounts positive.
- Enable and maintain Row Level Security on every table; keep RLS policies
  in sync with the API's per-user scoping.
- Long-running work (LLM categorization, bank import) runs as a background
  task, not inline in the request handler.

## File Organization

- `frontend/` — Next.js + TypeScript + CSS Modules app.
- `frontend/app/` (or `pages/`) — routes/pages.
- `frontend/components/` — reusable UI components, each with its own
  `*.module.css`.
- `backend/app/routers/` — FastAPI endpoints, grouped by resource.
- `backend/app/services/` — business logic (aggregation, categorization,
  import).
- `backend/app/schemas/` — Pydantic input/output models.
- `backend/tests/` — pytest tests.
- Repo root — `docker-compose.yml`, `.env.example` (committed),
  `.github/workflows/ci.yml`.
