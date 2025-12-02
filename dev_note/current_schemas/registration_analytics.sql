create table public.registration_analytics (
  id uuid not null default gen_random_uuid (),
  phone_number character varying(20) not null,
  event_type character varying(50) not null,
  step_number integer null,
  user_type character varying(20) null,
  error_field character varying(50) null,
  error_message text null,
  timestamp timestamp with time zone not null,
  created_at timestamp with time zone null default now(),
  constraint registration_analytics_pkey primary key (id),
  constraint registration_analytics_user_type_check check (
    (
      (user_type)::text = any (
        (
          array[
            'trainer'::character varying,
            'client'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_registration_analytics_phone on public.registration_analytics using btree (phone_number) TABLESPACE pg_default;

create index IF not exists idx_registration_analytics_event on public.registration_analytics using btree (event_type) TABLESPACE pg_default;

create index IF not exists idx_registration_analytics_timestamp on public.registration_analytics using btree ("timestamp") TABLESPACE pg_default;