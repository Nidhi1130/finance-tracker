<!-- BEGIN: finance-flow-agent-rules -->
# Finance Flow Frontend Rules

Before changing frontend code, read the root context docs in this order:

1. `../context/project-overview.md` - product goals, phases, scope, and success criteria
2. `../context/architecture.md` - stack, boundaries, storage model, and invariants
3. `../context/ui-context.md` - visual language, tokens, layout patterns, and component rules
4. `../context/code-standards.md` - implementation conventions and file organization
5. `../context/ai-workflow-rules.md` - workflow, scoping, and update rules
6. `../context/progress-tracker.md` - current phase, completed work, and next steps

## Rules

- The frontend talks only to FastAPI. Do not call Supabase or Postgres directly.
- Use CSS Modules for component styling.
- Keep shared styling tokens in `app/globals.css`.
- Use the Finance Flow color system, spacing, radius, and typography tokens from `../context/ui-context.md`.
- Keep changes small, focused, and easy to verify.
- Update `../context/progress-tracker.md` after any meaningful implementation change.
- If a requirement is unclear, resolve it in the context files before building.
<!-- END: finance-flow-agent-rules -->
