create table public.habit_tracking (
  id uuid not null default gen_random_uuid (),
  client_id uuid not null,
  habit_type character varying(50) not null,
  value text not null,
  date date not null default CURRENT_DATE,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  completed boolean null default true,
  constraint habit_tracking_pkey primary key (id),
  constraint unique_habit_per_day unique (client_id, habit_type, date),
  constraint habit_tracking_client_id_fkey foreign KEY (client_id) references clients (id) on delete CASCADE,
  constraint habit_tracking_habit_type_check check (
    (
      (habit_type)::text = any (
        (
          array[
            'water_intake'::character varying,
            'sleep_hours'::character varying,
            'steps'::character varying,
            'calories'::character varying,
            'workout_completed'::character varying,
            'meals_logged'::character varying,
            'weight'::character varying,
            'mood'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_habit_tracking_client on public.habit_tracking using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_habit_tracking_date on public.habit_tracking using btree (date) TABLESPACE pg_default;

create index IF not exists idx_habit_tracking_type on public.habit_tracking using btree (habit_type) TABLESPACE pg_default;

create index IF not exists idx_habit_tracking_client_date on public.habit_tracking using btree (client_id, date) TABLESPACE pg_default;