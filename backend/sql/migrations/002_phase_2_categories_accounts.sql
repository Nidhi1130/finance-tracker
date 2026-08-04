begin;

update categories set name = btrim(name);
update accounts set name = btrim(name);
update categories set color = '#6B7280' where color is null;
update categories set created_at = now() where created_at is null;
update accounts set created_at = now() where created_at is null;

alter table categories alter column color set not null;
alter table categories alter column created_at set not null;
alter table accounts alter column created_at set not null;

alter table categories drop constraint if exists categories_name_length_check;
alter table categories add constraint categories_name_length_check
  check (char_length(btrim(name)) between 1 and 80);
alter table categories drop constraint if exists categories_color_format_check;
alter table categories add constraint categories_color_format_check
  check (color ~ '^#[0-9A-F]{6}$');
alter table accounts drop constraint if exists accounts_name_length_check;
alter table accounts add constraint accounts_name_length_check
  check (char_length(btrim(name)) between 1 and 80);

alter table transactions drop constraint if exists transactions_category_id_fkey;
alter table transactions add constraint transactions_category_id_fkey
  foreign key (category_id) references categories(id) on delete set null;
alter table transactions drop constraint if exists transactions_account_id_fkey;
alter table transactions add constraint transactions_account_id_fkey
  foreign key (account_id) references accounts(id) on delete set null;

create unique index if not exists categories_owner_lower_name_key
  on categories (
    coalesce(user_id, '00000000-0000-0000-0000-000000000000'::uuid),
    lower(name)
  );
create unique index if not exists accounts_owner_lower_name_key
  on accounts (user_id, lower(name));
create index if not exists transactions_category_id_idx on transactions(category_id);
create index if not exists transactions_account_id_idx on transactions(account_id);

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

commit;
