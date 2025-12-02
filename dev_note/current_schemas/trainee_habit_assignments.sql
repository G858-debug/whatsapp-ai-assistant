create table public.trainee_habit_assignments (
  id uuid not null default gen_random_uuid (),
  habit_id character varying(10) not null,
  client_id character varying(10) not null,
  trainer_id character varying(10) not null,
  assigned_date timestamp with time zone null default now(),
  is_active boolean null default true,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint trainee_habit_assignments_pkey primary key (id),
  constraint trainee_habit_assignments_unique unique (habit_id, client_id),
  constraint trainee_habit_assignments_habit_fkey foreign KEY (habit_id) references fitness_habits (habit_id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_habit_assignments_client on public.trainee_habit_assignments using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_habit_assignments_habit on public.trainee_habit_assignments using btree (habit_id) TABLESPACE pg_default;

create index IF not exists idx_habit_assignments_trainer on public.trainee_habit_assignments using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_habit_assignments_active on public.trainee_habit_assignments using btree (is_active) TABLESPACE pg_default;

create index IF not exists idx_habit_assignments_client_active on public.trainee_habit_assignments using btree (client_id, is_active) TABLESPACE pg_default;

create trigger update_trainee_habit_assignments_updated_at BEFORE
update on trainee_habit_assignments for EACH row
execute FUNCTION update_updated_at_column ();