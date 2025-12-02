create table public.analytics_events (
  id uuid not null default gen_random_uuid (),
  event_type character varying(50) not null,
  user_id character varying(50) not null,
  user_type character varying(20) not null,
  metadata jsonb null default '{}'::jsonb,
  device_info jsonb null default '{}'::jsonb,
  timestamp timestamp with time zone not null,
  created_at timestamp with time zone null default now(),
  constraint analytics_events_pkey primary key (id),
  constraint analytics_events_user_type_check check (
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

create index IF not exists idx_analytics_events_user on public.analytics_events using btree (user_id, user_type) TABLESPACE pg_default;

create index IF not exists idx_analytics_events_type on public.analytics_events using btree (event_type) TABLESPACE pg_default;

create index IF not exists idx_analytics_events_timestamp on public.analytics_events using btree ("timestamp") TABLESPACE pg_default;
