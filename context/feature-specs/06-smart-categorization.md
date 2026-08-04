# Phase 4 — Smart Categorization

## Scope

Phase 4 categorizes new transactions in a background task without delaying the
create response. Deterministic user rules are the production default; OpenAI
is an optional, explicit server-side provider mode.

The priority order is:

1. a category selected by the user;
2. the best enabled keyword rule owned by that user;
3. the optional OpenAI provider when explicitly enabled;
4. uncategorized with status `not_requested`.

No provider is created in the default `rules` mode, even if an
`OPENAI_API_KEY` exists in the process environment.

## Data model

Migration `004_phase_4_smart_categorization.sql` adds:

- `transactions.category_source`: null, `manual`, `rule`, or `openai`;
- `transactions.categorization_status`: `not_requested`, `pending`,
  `categorized`, or `failed`;
- `transactions.categorized_at`: nullable categorization timestamp;
- `categorization_rules`: user-owned keyword-to-category rules.

`categorization_rules` contains `id`, `user_id`, `keyword`, `category_id`,
`enabled`, `created_at`, and `updated_at`. Keywords are trimmed to 1–120
characters and case-insensitively unique per user. The referenced category
must be global or owned by the same user. PostgreSQL enforces this with the
`categorization_rules_category_ownership` trigger.

RLS is enabled and forced. The `categorization_rules_own_rows` policy applies
the backend's transaction-local `app.user_id` to reads and writes. The unique
index on `(user_id, lower(keyword))` prevents duplicate normalized keywords.

The migration backfills existing categorized transactions as manual and
categorized. Existing uncategorized transactions retain no source and default
to `not_requested`.

## API contract

All endpoints require the existing verified Supabase bearer token. The user ID
comes only from its `sub` claim.

### Rules

- `GET /categorization-rules` lists the current user's rules with category
  name and color.
- `POST /categorization-rules` creates a rule.
- `PUT /categorization-rules/{rule_id}` changes keyword, category, or enabled
  state.
- `DELETE /categorization-rules/{rule_id}` deletes the rule.

Duplicate keywords return `409`; unavailable categories return `422`; missing
or another user's rule returns `404`.

### Transactions

Transaction responses include `category_source`, `categorization_status`, and
`categorized_at`.

A create request with a category records `manual`/`categorized` and schedules
no background work. A create request without a category records `pending` and
schedules categorization after the response.

`POST /transactions/{transaction_id}/categorize` retries an eligible
uncategorized transaction by returning it to `pending`. A manually categorized
transaction returns `409` so Retry cannot replace a user choice.

## Rule and provider behavior

Rule matching is a case-insensitive substring match over enabled rules. The
longest keyword wins; equal-length matches break ties by normalized keyword
then rule ID. A rule result is saved with source `rule` and status
`categorized` without calling any provider.

With `CATEGORIZATION_PROVIDER=rules` (the default), a no-match result is saved
as uncategorized with status `not_requested`. It is not an error and the UI
does not show Retry.

With `CATEGORIZATION_PROVIDER=openai`, a no-match rule result calls the
server-side OpenAI adapter. The adapter receives only normalized description,
transaction type, and visible category IDs/names. It must return one supplied
ID or null. A valid ID is saved with source `openai`; null becomes
`not_requested`; timeout, refusal, malformed output, invalid ID, missing key,
or provider error becomes `failed` and remains eligible for Retry.

Any other `CATEGORIZATION_PROVIDER` value raises a clear configuration error
during application startup.

## Concurrency and manual authority

The background task reloads the transaction and proceeds only while it remains
pending and uncategorized. The final database update repeats that condition
atomically. A manual edit changes the source to `manual` and status to
`categorized`, so a late rule or provider result cannot overwrite it.

Clearing a category manually resets the transaction to uncategorized and
`not_requested`; automation resumes only through explicit Retry. Multiple
background attempts are safe because only an eligible guarded write succeeds.

## Frontend behavior

- The empty category choice is labelled `Auto categorize`.
- Pending rows show `Categorizing…` and are polled every 1.5 seconds only while
  returned data still includes a pending transaction.
- Rule and OpenAI results show an accessible `Auto` badge naming the source.
- Manual categories have no Auto badge.
- Failed provider results show `Uncategorized` and Retry.
- Rules-mode no-match results show `Uncategorized` without Retry.
- `/rules` supports create, edit, enable/disable, and confirmed deletion.

When a user changes an automatically assigned category, the manual correction
is saved first. The optional `Save this as a rule` dialog is separate; dismissing
or failing it cannot roll back the transaction correction. Accepting creates an
editable rule visible on `/rules`.

Transaction and rule query keys include the authenticated user ID. Stateful
clients remount on session changes so pending queries, forms, dialogs, and
cached User A data cannot appear for User B.

## Configuration

Server-side variables:

- `CATEGORIZATION_PROVIDER=rules` — safe default; no OpenAI client or key;
- `CATEGORIZATION_PROVIDER=openai` — explicit optional provider mode;
- `OPENAI_API_KEY` — required only when OpenAI mode makes a provider request;
- `OPENAI_CATEGORIZATION_MODEL` — optional model override;
- `OPENAI_CATEGORIZATION_TIMEOUT_SECONDS` — optional timeout override.

Provider configuration and credentials never reach the frontend.

## Verification evidence — 2026-08-04

- Only migration 004 was applied to the configured remote Supabase database.
  Read-only checks confirmed the table, all columns, forced RLS, policy,
  ownership trigger, unique keyword index, constraints, and zero incomplete
  backfill rows. Three existing categorized rows were backfilled as manual.
- Rule-only smoke with an ambient OpenAI key confirmed provider `none`, a
  `spotify` rule result saved as categorized/rule, and an unmatched description
  saved as uncategorized/`not_requested`, with no OpenAI request.
- Backend: 89 tests passed against isolated PostgreSQL on port 5433; Ruff and
  lock verification passed. The sole warning is the existing Starlette
  TestClient/httpx deprecation.
- Frontend: 47 tests across 8 files passed; lint and production build passed.

## Explicit verification gap

No controllable browser was available in the release session, so authenticated
click-through coverage remains unavailable for manual bypass, rule badge,
rules-mode no-match, late-manual-wins, correction dismissal, correction-to-rule,
and real User A/User B isolation. These scenarios have automated regression
coverage but are not claimed as live browser observations.
