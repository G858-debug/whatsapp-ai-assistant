create table public.calendar_events (
  id uuid not null default gen_random_uuid (),
  booking_id uuid not null,
  external_event_id character varying(255) not null,
  provider character varying(20) not null,
  created_at timestamp with time zone null default now(),
  constraint calendar_events_pkey primary key (id),
  constraint calendar_events_booking_id_fkey foreign KEY (booking_id) references bookings (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_calendar_events_booking on public.calendar_events using btree (booking_id) TABLESPACE pg_default;

create index IF not exists idx_calendar_events_external on public.calendar_events using btree (external_event_id) TABLESPACE pg_default;