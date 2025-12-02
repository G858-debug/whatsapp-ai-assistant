create table public.bookings (
  id uuid not null default gen_random_uuid (),
  trainer_id uuid not null,
  client_id uuid not null,
  session_datetime timestamp with time zone not null,
  duration_minutes integer null default 60,
  price numeric(10, 2) not null,
  status character varying(20) null default 'scheduled'::character varying,
  session_notes text null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  session_date date null,
  session_time time without time zone null,
  session_type character varying(50) null default 'one_on_one'::character varying,
  notes text null,
  completion_notes text null,
  cancellation_reason text null,
  cancelled_at timestamp with time zone null,
  rescheduled_at timestamp with time zone null,
  completed_at timestamp with time zone null,
  constraint bookings_pkey primary key (id),
  constraint bookings_client_id_fkey foreign KEY (client_id) references clients (id) on delete CASCADE,
  constraint bookings_trainer_id_fkey foreign KEY (trainer_id) references trainers (id) on delete CASCADE,
  constraint bookings_status_check check (
    (
      (status)::text = any (
        (
          array[
            'scheduled'::character varying,
            'confirmed'::character varying,
            'completed'::character varying,
            'cancelled'::character varying,
            'no_show'::character varying,
            'rescheduled'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_bookings_date on public.bookings using btree (session_date) TABLESPACE pg_default;

create index IF not exists idx_bookings_session_type on public.bookings using btree (session_type) TABLESPACE pg_default;

create index IF not exists idx_bookings_completed_at on public.bookings using btree (completed_at) TABLESPACE pg_default;

create index IF not exists idx_bookings_cancelled_at on public.bookings using btree (cancelled_at) TABLESPACE pg_default;

create index IF not exists idx_bookings_trainer on public.bookings using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_bookings_client on public.bookings using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_bookings_datetime on public.bookings using btree (session_datetime) TABLESPACE pg_default;

create index IF not exists idx_bookings_status on public.bookings using btree (status) TABLESPACE pg_default;