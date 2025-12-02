create table public.calendar_sync_preferences (
  id uuid not null default gen_random_uuid (),
  trainer_id uuid not null,
  google_calendar_enabled boolean null default false,
  outlook_calendar_enabled boolean null default false,
  sync_frequency character varying(20) null default 'hourly'::character varying,
  auto_create_events boolean null default true,
  event_title_template character varying(255) null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint calendar_sync_preferences_pkey primary key (id),
  constraint calendar_sync_preferences_trainer_id_fkey foreign KEY (trainer_id) references trainers (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_calendar_sync_prefs_trainer on public.calendar_sync_preferences using btree (trainer_id) TABLESPACE pg_default;

create trigger update_calendar_sync_preferences_updated_at BEFORE
update on calendar_sync_preferences for EACH row
execute FUNCTION update_updated_at_column ();