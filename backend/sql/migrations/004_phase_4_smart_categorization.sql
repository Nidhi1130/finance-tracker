begin;

alter table transactions
  add column if not exists category_source text,
  add column if not exists categorization_status text not null default 'not_requested',
  add column if not exists categorized_at timestamptz;

update transactions
set category_source = 'manual',
    categorization_status = 'categorized',
    categorized_at = coalesce(categorized_at, updated_at)
where category_id is not null
  and category_source is null;

alter table transactions drop constraint if exists transactions_category_source_check;
alter table transactions add constraint transactions_category_source_check
  check (category_source is null or category_source in ('manual', 'rule', 'openai'));
alter table transactions drop constraint if exists transactions_categorization_status_check;
alter table transactions add constraint transactions_categorization_status_check
  check (categorization_status in ('not_requested', 'pending', 'categorized', 'failed'));

create table if not exists categorization_rules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  keyword text not null check (char_length(btrim(keyword)) between 1 and 120),
  category_id uuid not null references categories(id) on delete cascade,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists categorization_rules_user_lower_keyword_key
  on categorization_rules (user_id, lower(keyword));

create or replace function enforce_categorization_rule_category_ownership()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if not exists (
    select 1
    from categories
    where id = new.category_id
      and (user_id is null or user_id = new.user_id)
  ) then
    raise exception 'category_id is not available to this user'
      using errcode = '23514';
  end if;

  return new;
end;
$$;

drop trigger if exists categorization_rules_category_ownership on categorization_rules;
create trigger categorization_rules_category_ownership
before insert or update of user_id, category_id on categorization_rules
for each row execute function enforce_categorization_rule_category_ownership();

alter table categorization_rules enable row level security;

drop policy if exists categorization_rules_own_rows on categorization_rules;
create policy categorization_rules_own_rows
  on categorization_rules
  for all
  using (user_id = nullif(current_setting('app.user_id', true), '')::uuid)
  with check (user_id = nullif(current_setting('app.user_id', true), '')::uuid);

alter table categorization_rules force row level security;

commit;
