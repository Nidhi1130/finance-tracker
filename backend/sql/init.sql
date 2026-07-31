create extension if not exists pgcrypto;

create schema if not exists auth;

create table if not exists auth.users (
  id uuid primary key
);

create table if not exists categories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id),
  name text not null check (char_length(btrim(name)) between 1 and 80),
  color text not null check (color ~ '^#[0-9A-F]{6}$'),
  created_at timestamptz not null default now()
);

create table if not exists accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) not null,
  name text not null check (char_length(btrim(name)) between 1 and 80),
  created_at timestamptz not null default now()
);

create table if not exists transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) not null,
  amount numeric(12,2) not null check (amount >= 0),
  type text not null check (type in ('income', 'expense')),
  description text,
  date date not null,
  category_id uuid references categories(id) on delete set null,
  account_id uuid references accounts(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists categories_owner_lower_name_key
  on categories (
    coalesce(user_id, '00000000-0000-0000-0000-000000000000'::uuid),
    lower(name)
  );
create unique index if not exists accounts_owner_lower_name_key
  on accounts (user_id, lower(name));
create index if not exists transactions_category_id_idx on transactions(category_id);
create index if not exists transactions_account_id_idx on transactions(account_id);
create index if not exists transactions_user_date_idx on transactions(user_id, date);

alter table categories enable row level security;
alter table accounts enable row level security;
alter table transactions enable row level security;

drop policy if exists categories_read_own_or_global on categories;
create policy categories_read_own_or_global
  on categories
  for select
  using (
    user_id is null
    or user_id = nullif(current_setting('app.user_id', true), '')::uuid
  );

drop policy if exists categories_write_own on categories;
create policy categories_write_own
  on categories
  for all
  using (user_id = nullif(current_setting('app.user_id', true), '')::uuid)
  with check (user_id = nullif(current_setting('app.user_id', true), '')::uuid);

drop policy if exists accounts_own_rows on accounts;
create policy accounts_own_rows
  on accounts
  for all
  using (user_id = nullif(current_setting('app.user_id', true), '')::uuid)
  with check (user_id = nullif(current_setting('app.user_id', true), '')::uuid);

drop policy if exists transactions_own_rows on transactions;
create policy transactions_own_rows
  on transactions
  for all
  using (user_id = nullif(current_setting('app.user_id', true), '')::uuid)
  with check (user_id = nullif(current_setting('app.user_id', true), '')::uuid);

insert into categories (id, user_id, name, color)
values
  ('00000000-0000-4000-8000-000000000001', null, 'Housing', '#7C3AED'),
  ('00000000-0000-4000-8000-000000000002', null, 'Groceries', '#16A34A'),
  ('00000000-0000-4000-8000-000000000003', null, 'Dining', '#EA580C'),
  ('00000000-0000-4000-8000-000000000004', null, 'Transport', '#2563EB'),
  ('00000000-0000-4000-8000-000000000005', null, 'Utilities', '#0891B2'),
  ('00000000-0000-4000-8000-000000000006', null, 'Health', '#DC2626'),
  ('00000000-0000-4000-8000-000000000007', null, 'Entertainment', '#DB2777'),
  ('00000000-0000-4000-8000-000000000008', null, 'Shopping', '#CA8A04'),
  ('00000000-0000-4000-8000-000000000009', null, 'Salary', '#059669'),
  ('00000000-0000-4000-8000-000000000010', null, 'Other', '#6B7280')
on conflict (id) do update
set user_id = null,
    name = excluded.name,
    color = excluded.color;

create or replace function enforce_transaction_reference_ownership()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if new.category_id is not null and not exists (
    select 1
    from categories
    where id = new.category_id
      and (user_id is null or user_id = new.user_id)
  ) then
    raise exception 'category_id is not available to this user'
      using errcode = '23514';
  end if;

  if new.account_id is not null and not exists (
    select 1
    from accounts
    where id = new.account_id
      and user_id = new.user_id
  ) then
    raise exception 'account_id is not available to this user'
      using errcode = '23514';
  end if;

  return new;
end;
$$;

drop trigger if exists transactions_reference_ownership on transactions;
create trigger transactions_reference_ownership
before insert or update of user_id, category_id, account_id on transactions
for each row execute function enforce_transaction_reference_ownership();

alter table categories force row level security;
alter table accounts force row level security;
alter table transactions force row level security;
