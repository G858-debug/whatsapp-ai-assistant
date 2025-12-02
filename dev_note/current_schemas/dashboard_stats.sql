create table public.dashboard_stats (
  id uuid not null default gen_random_uuid (),
  trainer_id uuid null,
  stat_date date not null,
  total_clients integer null default 0,
  active_clients integer null default 0,
  sessions_completed integer null default 0,
  sessions_cancelled integer null default 0,
  revenue_amount numeric(10, 2) null default 0,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint dashboard_stats_pkey primary key (id),
  constraint dashboard_stats_trainer_id_fkey foreign KEY (trainer_id) references trainers (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_dashboard_stats_trainer on public.dashboard_stats using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_dashboard_stats_date on public.dashboard_stats using btree (stat_date) TABLESPACE pg_default;

create trigger update_dashboard_stats_updated_at BEFORE
update on dashboard_stats for EACH row
execute FUNCTION update_updated_at_column ();