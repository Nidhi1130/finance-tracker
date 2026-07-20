# 02 - App Shell Navigation

## Start Here

Read `frontend/AGENTS.md` before changing frontend code.

## Purpose

Create the Finance Flow top app shell that frames the dashboard and future
pages without copying the editor/sidebar pattern from the sample image.

## Required Direction

- Use CSS Modules for component styles.
- Keep shared design tokens in `frontend/app/globals.css`.
- Use the Finance Flow visual system from `context/ui-context.md`.
- Keep the frontend talking only to FastAPI.
- Do not call Supabase or Postgres directly from the browser.

## What This Shell Must Provide

### Layout

- A top navbar with a bottom border.
- A clear brand area for Finance Flow.
- A navigation area for the main app sections.
- A right-side utility area for actions or status.
- A main content area below the nav that does not shift when navigation
  changes.
- Responsive behavior for desktop and mobile.

### Navigation

- Show the primary Finance Flow sections needed for the early app:
  - Dashboard
  - Transactions
  - Categories
  - Accounts
- Keep navigation simple and readable.
- Use an active state for the current page.

### Styling

- Use CSS Modules for the shell and navigation pieces.
- Keep styles scoped to the shell component files.
- Use the project tokens from `context/ui-context.md`.
- Avoid hardcoded colors where tokens already exist.

### Utility

- Reuse the shared `cn()` helper if class composition is needed.
- Keep utility code minimal.

## Do Not Add

- left sidebar navigation
- editor-style floating panels
- shadcn/ui
- Tailwind CSS
- direct database access from the frontend
- authentication flows
- dashboard charts

## Done When

- The app has a top navbar shell that matches Finance Flow requirements.
- The layout stays stable when navigation is added.
- The shell uses the existing CSS Module and token system.
- The code matches `context/project-overview.md`,
  `context/architecture.md`, `context/code-standards.md`, and
  `context/ui-context.md`.

