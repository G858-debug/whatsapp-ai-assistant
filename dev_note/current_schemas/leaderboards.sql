create table public.leaderboards (
  id uuid not null default gen_random_uuid (),
  trainer_id uuid not null,
  leaderboard_type character varying(50) not null,
  period_start date not null,
  period_end date not null,
  rankings jsonb not null default '[]'::jsonb,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint leaderboards_pkey primary key (id),
  constraint leaderboards_trainer_id_fkey foreign KEY (trainer_id) references trainers (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_leaderboards_trainer on public.leaderboards using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_leaderboards_type on public.leaderboards using btree (leaderboard_type) TABLESPACE pg_default;

create index IF not exists idx_leaderboards_period on public.leaderboards using btree (period_start, period_end) TABLESPACE pg_default;

create trigger update_leaderboards_updated_at BEFORE
update on leaderboards for EACH row
execute FUNCTION update_updated_at_column ();