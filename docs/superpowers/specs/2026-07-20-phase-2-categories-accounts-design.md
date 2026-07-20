# Phase 2: Categories and Accounts Design

## Objective

Phase 2 adds user-managed categories and accounts across Postgres, FastAPI,
and Next.js. Signed-in users can create, list, edit, and delete their own
resources. Everyone can read a fixed set of global categories, but normal
users cannot mutate them. Transaction forms and filters use these resources
by name instead of requiring raw UUID input.

The authenticated user ID always comes from the verified Supabase JWT `sub`
claim. The frontend continues to call FastAPI only.

## Delivery Approach

Implementation proceeds as independently verifiable vertical slices:

1. Database rules and backend category/account contracts.
2. Category and account management pages.
3. Transaction selector/filter integration.
4. Cross-cutting verification, documentation, and smoke testing.

Discovery work may run in parallel, but implementation tasks that share API
contracts or files run in dependency order. Each task receives an independent
review before the next dependent task starts.

## Data Model

### Categories

`categories` contains:

- `id uuid primary key`
- `user_id uuid null references auth.users(id)`
- `name text not null`
- `color text not null`
- `created_at timestamptz not null default now()`

`user_id is null` identifies a global category. User-created categories always
receive the JWT-derived user ID; clients cannot submit `user_id`.

Names are trimmed, contain 1–80 characters after trimming, and are unique
case-insensitively within one ownership scope. A user may create a custom
category whose name matches a global category because the rows have different
ownership scopes. Colors must match `^#[0-9A-Fa-f]{6}$` and are normalized to
uppercase before storage and output.

The migration seeds these immutable global categories with stable UUIDs:

| ID | Name | Color |
| --- | --- | --- |
| `00000000-0000-4000-8000-000000000001` | Housing | `#7C3AED` |
| `00000000-0000-4000-8000-000000000002` | Groceries | `#16A34A` |
| `00000000-0000-4000-8000-000000000003` | Dining | `#EA580C` |
| `00000000-0000-4000-8000-000000000004` | Transport | `#2563EB` |
| `00000000-0000-4000-8000-000000000005` | Utilities | `#0891B2` |
| `00000000-0000-4000-8000-000000000006` | Health | `#DC2626` |
| `00000000-0000-4000-8000-000000000007` | Entertainment | `#DB2777` |
| `00000000-0000-4000-8000-000000000008` | Shopping | `#CA8A04` |
| `00000000-0000-4000-8000-000000000009` | Salary | `#059669` |
| `00000000-0000-4000-8000-000000000010` | Other | `#6B7280` |

### Accounts

`accounts` contains:

- `id uuid primary key`
- `user_id uuid not null references auth.users(id)`
- `name text not null`
- `created_at timestamptz not null default now()`

The Phase 2 account model intentionally has no `type` field. Checking,
savings, and cash are example names rather than an enum. Names are trimmed,
contain 1–80 characters after trimming, and are unique case-insensitively per
user.

### Transaction references and deletion

`transactions.category_id` and `transactions.account_id` remain nullable.
Their foreign keys use `ON DELETE SET NULL`. Deleting a custom category or
account preserves every transaction and clears only the deleted reference.

Transaction create and update operations validate references before writing:

- a category must be global or owned by the current user;
- an account must be owned by the current user;
- an unknown or inaccessible reference returns `422` with a field-specific
  validation message.

## Migration and Row-Level Security

Phase 2 adds an idempotent, additive SQL migration rather than rewriting
already-applied schema history. The local bootstrap remains capable of
building the final schema on a fresh database.

Before making category color non-null, the migration converts any existing
null color to `#6B7280`. It replaces both transaction foreign keys with
`ON DELETE SET NULL`, adds case-insensitive per-owner uniqueness indexes, and
inserts the defaults by stable ID with conflict-safe statements.

RLS is enabled and forced on `categories`, `accounts`, and `transactions` so
the table owner does not silently bypass policies during application queries.
Each backend database session sets transaction-local `app.user_id` from the
verified JWT subject before accessing protected rows.

Policies are:

- categories `SELECT`: `user_id is null` or `user_id = app.user_id`;
- categories `INSERT`, `UPDATE`, and `DELETE`: `user_id = app.user_id`;
- accounts all operations: `user_id = app.user_id`;
- transactions all operations: `user_id = app.user_id`.

The API never exposes mutation endpoints capable of creating or changing
global categories. RLS remains the defense-in-depth boundary. Ownership and
filter columns receive indexes suitable for category/account lists and
transaction filters.

A database trigger also rejects a transaction category that is neither global
nor owned by `NEW.user_id`, and rejects an account not owned by `NEW.user_id`.
This complements the API's readable validation errors and prevents an
incorrect future query from creating cross-user references.

## Backend API Contract

All endpoints require authentication and use the verified JWT `sub` UUID.
Collection responses use the existing `{ "items": [...] }` envelope.

### Category schemas

`CategoryCreate`:

```json
{ "name": "Travel", "color": "#2563EB" }
```

`CategoryUpdate` has the same required fields. `CategoryOut` is:

```json
{
  "id": "uuid",
  "name": "Travel",
  "color": "#2563EB",
  "is_global": false,
  "created_at": "2026-07-20T10:00:00Z"
}
```

Routes:

- `GET /categories` → `200`, global defaults followed by the current user's
  custom categories, each group ordered case-insensitively by name;
- `POST /categories` → `201`;
- `PUT /categories/{category_id}` → `200`;
- `DELETE /categories/{category_id}` → `204`.

Mutating a visible global category returns `403`. A missing or another user's
category returns `404`. A malformed UUID path returns `422`. Duplicate names
within the user's custom categories return `409`.

### Account schemas

`AccountCreate` and `AccountUpdate`:

```json
{ "name": "Main checking" }
```

`AccountOut` is:

```json
{
  "id": "uuid",
  "name": "Main checking",
  "created_at": "2026-07-20T10:00:00Z"
}
```

Routes:

- `GET /accounts` → `200`, current user's accounts ordered
  case-insensitively by name;
- `POST /accounts` → `201`;
- `PUT /accounts/{account_id}` → `200`;
- `DELETE /accounts/{account_id}` → `204`.

Missing or inaccessible accounts return `404`; malformed UUIDs return `422`;
duplicate names for the same user return `409`.

### Transaction integration

`GET /transactions` retains existing filters and adds optional
`account_id=<uuid>`. The backend repository applies both category and account
filters while preserving JWT-derived ownership scoping.

## Backend Organization

The existing repository module is already large, so Phase 2 introduces a
repository package with focused modules rather than extending one monolith.
Transaction behavior remains compatible while shared Postgres session setup
is centralized. Routers remain thin: parse Pydantic input, obtain the current
user, call a repository/service boundary, and translate domain outcomes to
HTTP responses.

In-memory repositories mirror Postgres behavior, including global defaults,
ownership isolation, duplicate detection, reference validation, and nulling
transaction references after deletion. Real Postgres integration tests cover
RLS rather than assuming in-memory tests prove database policies.

## Frontend Design

### Shared data boundary

`frontend/lib/api.ts` owns authenticated JSON requests, FastAPI error-detail
extraction, and the API base URL. Resource-specific modules own strict DTOs,
query keys, and CRUD functions. Query keys include the authenticated user ID
so switching users cannot reuse protected cached data.

### Categories page

The Categories route remains a thin page around an interactive client
component. It provides:

- authentication-required, loading, error, and empty states;
- a read-only Global defaults section with color swatches and a Default badge;
- a Custom categories section;
- create and edit forms in the existing modal primitive;
- explicit labels, inline validation, pending states, and delete confirmation;
- Edit/Delete actions only for custom categories.

### Accounts page

The Accounts page mirrors the management flow without color input. Users can
create, edit, and delete named accounts with confirmation and clear mutation
feedback.

### Transactions page

The transaction client loads categories and accounts through TanStack Query.
Raw UUID inputs become labeled native selects:

- form category: `Uncategorized` plus global/custom categories;
- form account: `No account` plus the user's accounts;
- filters: `All categories` and `All accounts` plus resource options.

The list displays names instead of IDs and uses a safe fallback if a referenced
row is unavailable. Account filtering adds `account_id` to the query string.
Deleting a referenced category/account invalidates transaction queries so the
cleared labels render immediately.

All new styling uses CSS Modules and existing global tokens. No component
library or direct Supabase data access is introduced.

## Error Handling

The shared API helper extracts FastAPI `detail` values and produces readable
messages. Forms keep user input after a failed mutation. Buttons and fields are
disabled only while their own mutation is pending. Deletion requires explicit
confirmation. A refetch occurs after successful mutations through targeted
TanStack Query invalidation.

## Test Strategy

Backend HTTP tests cover:

- category and account create/list/update/delete;
- global defaults included in every authenticated category list;
- global defaults immutable;
- per-user list and mutation isolation;
- required/blank/overlong names, invalid colors, duplicates, malformed UUIDs,
  and valid-but-missing UUIDs;
- accepted global/owned category references;
- rejected cross-user category/account references;
- category and account transaction filtering;
- deletion clearing transaction references.

Postgres integration tests cover forced RLS with two users, global visibility,
global immutability, cross-user isolation, and cross-user transaction-reference
rejection. Tests may skip only when the documented integration database URL is
absent; CI supplies the database service so the RLS suite runs there.

Verification commands are:

```bash
cd backend
.venv/bin/ruff check app tests
.venv/bin/pytest

cd ../frontend
npm run lint
npm run build
```

The local UI smoke test signs in, confirms defaults, completes custom category
and account CRUD, creates/edits a transaction through named selectors, filters
by both resources, deletes the referenced resources, and confirms the
transaction remains with cleared references.

## Documentation and Progress

Implementation adds a Phase 2 feature spec under `context/feature-specs/`,
updates `architecture.md` for the locked schema/RLS rules, and updates
`progress-tracker.md` after each meaningful slice. The previous open question
deferring Accounts UI/CRUD is removed because this approved Phase 2 explicitly
includes it.

## Agent Ownership

1. Backend/data agent: migration, RLS, schemas, repositories, routers,
   transaction validation/filtering, and backend tests.
2. Resource-management frontend agent: shared API boundary plus Categories and
   Accounts CRUD pages.
3. Transaction-integration agent: selectors, label rendering, category/account
   filters, cache invalidation, and UI smoke preparation.
4. Independent reviewers: task-level spec/quality review after each slice and a
   final whole-branch review before completion.
