create table public.habit_reminder_preferences (
  id uuid not null default gen_random_uuid (),
  client_id character varying(10) not null,
  reminder_enabled boolean null default true,
  reminder_time time without time zone null default '09:00:00'::time without time zone,
  timezone character varying(50) null default 'UTC'::character varying,
  reminder_days integer[] null default '{1,2,3,4,5,6,7}'::integer[],
  include_progress boolean null default true,
  include_encouragement boolean null default true,
  last_updated timestamp with time zone null default now(),
  created_at timestamp with time zone null default now(),
  constraint habit_reminder_preferences_pkey primary key (id),
  constraint habit_reminder_preferences_client_unique unique (client_id)
) TABLESPACE pg_default;

create index IF not exists idx_habit_reminder_prefs_client on public.habit_reminder_preferences using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_habit_reminder_prefs_enabled on public.habit_reminder_preferences using btree (reminder_enabled) TABLESPACE pg_default;