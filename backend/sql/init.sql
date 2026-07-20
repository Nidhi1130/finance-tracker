create extension if not exists pgcrypto;

create schema if not exists auth;

create table if not exists auth.users (
  id uuid primary key
);

create table if not exists categories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id),
  name text not null,
  color text,
  created_at timestamptz default now()
);

create table if not exists accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) not null,
  name text not null,
  created_at timestamptz default now()
);

create table if not exists transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) not null,
  amount numeric(12,2) not null check (amount >= 0),
  type text not null check (type in ('income', 'expense')),
  description text,
  date date not null,
  category_id uuid references categories(id),
  account_id uuid references accounts(id),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table categories enable row level security;
alter table accounts enable row level security;
alter table transactions enable row level security;

drop policy if exists categories_read_own_or_global on categories;
create policy categories_read_own_or_global
  on categories
  for select
  using (user_id is null or user_id = current_setting('app.user_id', true)::uuid);

drop policy if exists categories_write_own on categories;
create policy categories_write_own
  on categories
  for all
  using (user_id = current_setting('app.user_id', true)::uuid)
  with check (user_id = current_setting('app.user_id', true)::uuid);

drop policy if exists accounts_own_rows on accounts;
create policy accounts_own_rows
  on accounts
  for all
  using (user_id = current_setting('app.user_id', true)::uuid)
  with check (user_id = current_setting('app.user_id', true)::uuid);

drop policy if exists transactions_own_rows on transactions;
create policy transactions_own_rows
  on transactions
  for all
  using (user_id = current_setting('app.user_id', true)::uuid)
  with check (user_id = current_setting('app.user_id', true)::uuid);
