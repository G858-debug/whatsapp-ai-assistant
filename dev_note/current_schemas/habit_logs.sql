create table public.habit_logs (
  id uuid not null default gen_random_uuid (),
  habit_id character varying(10) not null,
  client_id character varying(10) not null,
  log_date date not null,
  log_time timestamp with time zone null default now(),
  completed_value numeric(10, 2) not null,
  notes text null,
  created_at timestamp with time zone null default now(),
  constraint habit_logs_pkey primary key (id),
  constraint habit_logs_habit_fkey foreign KEY (habit_id) references fitness_habits (habit_id) on delete CASCADE,
  constraint habit_logs_completed_value_check check ((completed_value >= (0)::numeric))
) TABLESPACE pg_default;

create index IF not exists idx_habit_logs_client on public.habit_logs using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_habit_logs_habit on public.habit_logs using btree (habit_id) TABLESPACE pg_default;

create index IF not exists idx_habit_logs_date on public.habit_logs using btree (log_date) TABLESPACE pg_default;

create index IF not exists idx_habit_logs_client_date on public.habit_logs using btree (client_id, log_date) TABLESPACE pg_default;

create index IF not exists idx_habit_logs_habit_date on public.habit_logs using btree (habit_id, log_date) TABLESPACE pg_default;

create index IF not exists idx_habit_logs_client_habit_date on public.habit_logs using btree (client_id, habit_id, log_date) TABLESPACE pg_default;

create index IF not exists idx_habit_logs_time on public.habit_logs using btree (log_time desc) TABLESPACE pg_default;