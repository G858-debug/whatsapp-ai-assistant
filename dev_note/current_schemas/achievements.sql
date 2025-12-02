create table public.achievements (
  id uuid not null default gen_random_uuid (),
  client_id uuid not null,
  trainer_id uuid not null,
  achievement_type character varying(50) not null,
  achievement_name character varying(100) not null,
  description text null,
  points_awarded integer null default 0,
  unlocked_at timestamp with time zone null default now(),
  created_at timestamp with time zone null default now(),
  constraint achievements_pkey primary key (id),
  constraint achievements_client_id_fkey foreign KEY (client_id) references clients (id) on delete CASCADE,
  constraint achievements_trainer_id_fkey foreign KEY (trainer_id) references trainers (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_achievements_client on public.achievements using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_achievements_trainer on public.achievements using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_achievements_type on public.achievements using btree (achievement_type) TABLESPACE pg_default;