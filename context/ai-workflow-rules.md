# AI Workflow Rules

## Approach

Build this project incrementally using a spec-driven, phase-by-phase
workflow. The context files define what to build (`project-overview.md`),
how the system is shaped (`architecture.md`), the conventions
(`code-standards.md`), the visual language (`ui-context.md`), and the
current state (`progress-tracker.md`). Always implement against these specs
and against the phase definitions in the project guide — do not infer or
invent behavior from scratch. Build phases strictly in order; do not start
a phase until the previous one's "done when" criteria are met. Each phase
must end as a working, demoable app.

## Scoping Rules

- Work on one feature unit at a time (one endpoint + its UI, or one
  aggregation query + its chart).
- Prefer small, verifiable increments over large speculative changes.
- Do not combine unrelated system boundaries in a single implementation
  step.

## When to Split Work

Split an implementation step if it combines:

- Frontend (Next.js) changes and backend (FastAPI) changes that can't each
  be verified on their own.
- Multiple unrelated API routes or resources in one step.
- Inline request handling and background-task work (e.g. CRUD + LLM
  categorization) in the same step.
- Behavior that is not clearly defined in the context files or the phase
  spec.

If a change cannot be verified end to end quickly (via `/docs`, the UI, or
a test), the scope is too broad — split it.

## Handling Missing Requirements

- Do not invent product behavior not defined in the context files or the
  phase spec.
- If a requirement is ambiguous, resolve it in the relevant context file
  before implementing.
- If a requirement is missing, add it as an open question in
  `progress-tracker.md` before continuing.

## Protected Files

Do not modify the following unless explicitly instructed:

- Supabase-managed auth (`auth.users`) — reference it, never rebuild it.
- Applied database migrations / schema history — add a new migration
  rather than editing an old one.
- Any third-party library internals.
- Generated files (e.g. lockfiles, generated API/types) — regenerate them
  via their tool, don't hand-edit.

## Keeping Docs in Sync

Update the relevant context file whenever implementation changes:

- System architecture or boundaries → `architecture.md`
- Storage model or schema decisions → `architecture.md`
- Code conventions or standards → `code-standards.md`
- Visual tokens or layout patterns → `ui-context.md`
- Feature scope → `project-overview.md`
- Always update `progress-tracker.md` after a meaningful change.

## Before Moving to the Next Unit

1. The current unit works end to end within its defined scope.
2. No invariant defined in `architecture.md` was violated (frontend →
   FastAPI → DB only; JWT-derived user id; numeric money; per-user
   scoping).
3. `progress-tracker.md` reflects the completed work.
4. The build and checks pass:
   - Backend: `ruff check` clean and `pytest` green.
   - Frontend: `npm run build` passes and the frontend test runner is
     green.
   - CI is green on push.
