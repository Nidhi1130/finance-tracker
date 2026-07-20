# 03 - Transactions CRUD

## Start Here

Read `frontend/AGENTS.md` and `context/feature-specs/01-foundation.md`
before changing code.

## Purpose

Let a signed-in Finance Flow user create, view, edit, delete, and filter
transactions. Each transaction belongs to the authenticated user and can
reference a category plus an optional account.

## Required Direction

- Use the Finance Flow architecture from `context/architecture.md`.
- Keep the frontend talking only to FastAPI.
- Keep the backend as the only component that owns transaction state.
- Money is stored as `numeric(12,2)` and amounts stay positive.
- The authenticated user id comes from the JWT, never from the request
  body.
- Categories support global defaults with `user_id = null`.

## Data Model

### Users

- Supabase Auth provides `auth.users`.
- Do not build a custom users table.

### Categories

- `id uuid primary key default gen_random_uuid()`
- `user_id uuid references auth.users(id)` nullable for global defaults
- `name text not null`
- `color text` optional
- `created_at timestamptz default now()`

### Accounts

- Optional in this phase.
- `id uuid primary key default gen_random_uuid()`
- `user_id uuid references auth.users(id) not null`
- `name text not null`
- `created_at timestamptz default now()`

### Transactions

- `id uuid primary key default gen_random_uuid()`
- `user_id uuid references auth.users(id) not null`
- `amount numeric(12,2) not null check (amount >= 0)`
- `type text not null check (type in ('income', 'expense'))`
- `description text`
- `date date not null`
- `category_id uuid references categories(id)`
- `account_id uuid references accounts(id)`
- `created_at timestamptz default now()`
- `updated_at timestamptz default now()`

### Money Rule

- Use numeric/Decimal end to end.
- Never use float for money.
- Store amount as a positive value.
- Use `type` to decide income versus expense direction.

## Pydantic Schemas

```python
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field

class TxType(str, Enum):
    income = "income"
    expense = "expense"

class TransactionCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    type: TxType
    description: str | None = None
    date: date
    category_id: UUID | None = None
    account_id: UUID | None = None

class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    type: TxType | None = None
    description: str | None = None
    date: date | None = None
    category_id: UUID | None = None
    account_id: UUID | None = None

class TransactionOut(BaseModel):
    id: UUID
    amount: Decimal
    type: TxType
    description: str | None
    date: date
    category_id: UUID | None
    account_id: UUID | None
    created_at: datetime
    updated_at: datetime
```

## API Endpoints

- All routes require an authenticated user.
- The user id comes from the JWT, never the body.
- CRUD routes:
  - `GET /transactions`
  - `POST /transactions`
  - `GET /transactions/{id}`
  - `PUT /transactions/{id}`
  - `DELETE /transactions/{id}`
- List filters:
  - `from=YYYY-MM-DD`
  - `to=YYYY-MM-DD`
  - `type=income|expense`
  - `category_id=uuid`

## Frontend

- Transaction list page.
- Create/edit transaction form.
- Delete action.
- Use TanStack Query for fetching and caching.
- Use scoped CSS Modules per component.
- Keep the page aligned with the Finance Flow shell/navigation.

## Tests

- Add 2-3 pytest tests for:
  - create
  - list
  - delete
- Assert validation rejects:
  - a negative amount
  - a bad transaction type

## Do Not Add

- direct database access from the browser
- float money handling
- unrelated dashboard charts
- bank import
- categorization automation

## Done When

- A logged-in user can add, edit, list, and delete transactions through
  the UI.
- Transactions accept category and optional account references.
- Filters work for the supported fields.
- The backend and frontend match this spec.
- Tests pass in CI.
