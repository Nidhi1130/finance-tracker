# 01 - Frontend Foundation

## Start Here

Read `frontend/AGENTS.md` before changing frontend code.

## Purpose

Build the first reusable frontend layer for Finance Flow so later screens can
share the same layout, tokens, and component patterns.

## Required Direction

- Use CSS Modules for component styles.
- Keep shared design tokens in `frontend/app/globals.css`.
- Use the Finance Flow visual system from `context/ui-context.md`.
- Keep the frontend talking only to FastAPI.
- Do not call Supabase or Postgres directly from the browser.

## What This Foundation Must Provide

### Layout

- A simple app shell that works for Finance Flow pages.
- Centered standalone screen patterns where appropriate.
- Responsive behavior for desktop and mobile.

### Shared UI

Create reusable primitives in `frontend/components/` for the UI work that
comes next:

- `Button`
- `Card`
- `Input`
- `Modal` or `Dialog`
- `Tabs`
- `Textarea`
- `ScrollArea` if longer content needs it

Each primitive must use its own `*.module.css` file.

### Styling

- Put global tokens in `frontend/app/globals.css`.
- Use the color, radius, typography, and spacing decisions from
  `context/ui-context.md`.
- Avoid hardcoded colors where tokens already exist.
- Keep component styles scoped.

### Utility

- Add a small `cn()` helper only if class composition needs it.
- Keep utility code minimal.

### Icons

- Use Lucide React if icons are needed.
- Keep icon usage simple and consistent.

## Do Not Add

- shadcn/ui
- Tailwind CSS
- direct database access from the frontend
- authentication flows
- dashboard charts
- transaction CRUD

## Done When

- The frontend has a clean CSS Module base.
- The app shell and shared primitives are ready for Phase 1 and Phase 2 work.
- The code matches `context/project-overview.md`,
  `context/architecture.md`, `context/code-standards.md`, and
  `context/ui-context.md`.

