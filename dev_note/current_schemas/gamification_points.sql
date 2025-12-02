create table public.gamification_points (
  id uuid not null default gen_random_uuid (),
  client_id uuid not null,
  trainer_id uuid not null,
  points integer not null default 0,
  reason character varying(100) not null,
  activity_type character varying(50) not null,
  activity_data jsonb null default '{}'::jsonb,
  created_at timestamp with time zone null default now(),
  constraint gamification_points_pkey primary key (id),
  constraint gamification_points_client_id_fkey foreign KEY (client_id) references clients (id) on delete CASCADE,
  constraint gamification_points_trainer_id_fkey foreign KEY (trainer_id) references trainers (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_gamification_points_client on public.gamification_points using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_gamification_points_trainer on public.gamification_points using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_gamification_points_activity on public.gamification_points using btree (activity_type) TABLESPACE pg_default;