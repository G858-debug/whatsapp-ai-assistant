create table public.calendar_sync_status (
  id uuid not null default gen_random_uuid (),
  trainer_id uuid not null,
  provider character varying(20) not null,
  last_sync timestamp with time zone null,
  sync_status character varying(20) null default 'pending'::character varying,
  events_synced integer null default 0,
  error_message text null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint calendar_sync_status_pkey primary key (id),
  constraint calendar_sync_status_trainer_id_fkey foreign KEY (trainer_id) references trainers (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_calendar_sync_status_trainer on public.calendar_sync_status using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_calendar_sync_status_provider on public.calendar_sync_status using btree (provider) TABLESPACE pg_default;

create trigger update_calendar_sync_status_updated_at BEFORE
update on calendar_sync_status for EACH row
execute FUNCTION update_updated_at_column ();