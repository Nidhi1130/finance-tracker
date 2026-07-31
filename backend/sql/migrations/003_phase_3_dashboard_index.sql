begin;

create index if not exists transactions_user_date_idx
  on transactions(user_id, date);

commit;
