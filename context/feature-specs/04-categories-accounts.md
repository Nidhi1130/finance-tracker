# Phase 2 — Categories and Accounts

## Goal

Signed-in users can manage their own categories and accounts, use them on
transactions, and filter transactions by either resource. FastAPI remains the
only database client and derives ownership from the verified Supabase JWT
`sub` claim.

## Data model

Categories contain `id`, nullable `user_id`, `name`, `color`, and
`created_at`. Accounts contain `id`, required `user_id`, `name`, and
`created_at`. Account type is intentionally out of scope.

Names are trimmed and contain 1–80 characters. Names are unique
case-insensitively within an ownership scope. Colors use uppercase
`#RRGGBB`. Custom category names may match global names.

Global categories have `user_id is null`, are readable by every authenticated
user, and cannot be changed by normal users:

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

Transaction category/account foreign keys use `ON DELETE SET NULL`; deleting
a resource preserves the transaction. A transaction category must be global
or owned by its user. A transaction account must be owned by its user.

## RLS

RLS is enabled and forced on categories, accounts, and transactions.
Categories permit reads of global or current-user rows and writes only to
current-user rows. Accounts and transactions permit access only to
current-user rows. Each backend transaction sets local `app.user_id` from the
verified JWT subject. A database trigger rejects cross-user transaction
references as defense in depth.

## API contract

All routes require authentication. Collection responses use `{ "items": [] }`.

- `GET /categories` returns globals first, then the user's categories.
- `POST /categories` returns `201`.
- `PUT /categories/{id}` returns `200`.
- `DELETE /categories/{id}` returns `204`.
- `GET /accounts` returns the user's accounts.
- `POST /accounts` returns `201`.
- `PUT /accounts/{id}` returns `200`.
- `DELETE /accounts/{id}` returns `204`.
- `GET /transactions` adds optional `account_id` filtering.

Category output includes `id`, `name`, `color`, `is_global`, and
`created_at`. Account output includes `id`, `name`, and `created_at`.
Duplicate user-owned names return `409`. Global-category mutation returns
`403`. Missing or inaccessible rows return `404`. Malformed UUIDs and invalid
request fields return `422`.

## Frontend contract

Categories and Accounts pages provide authenticated create/edit/delete flows
with accessible labels, pending/error states, and delete confirmation. Global
categories appear separately without mutation actions. Transaction category
and account inputs and filters are named selectors rather than raw UUID fields.
Transaction tables show names with safe unavailable-resource fallbacks.

All data uses TanStack Query through FastAPI. Query keys include the current
user ID to prevent protected cache reuse when accounts switch.

## Tests and completion

Backend tests cover CRUD, required fields, invalid colors/UUIDs, duplicate
names, global visibility/immutability, per-user isolation, reference ownership,
account/category filters, and delete nulling. Postgres integration tests cover
forced RLS and the ownership trigger with two users.

Phase 2 is complete when backend pytest/Ruff and frontend lint/build pass and a
signed-in smoke test verifies management pages, selectors, filters, isolation,
and preserved transactions after resource deletion.
