create table public.activity_logs (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  user_type character varying(20) not null,
  activity_type character varying(50) not null,
  activity_data jsonb null default '{}'::jsonb,
  ip_address inet null,
  user_agent text null,
  created_at timestamp with time zone null default now(),
  constraint activity_logs_pkey primary key (id),
  constraint activity_logs_user_type_check check (
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

create index IF not exists idx_activity_logs_user on public.activity_logs using btree (user_id, user_type) TABLESPACE pg_default;

create index IF not exists idx_activity_logs_type on public.activity_logs using btree (activity_type) TABLESPACE pg_default;

create index IF not exists idx_activity_logs_created on public.activity_logs using btree (created_at) TABLESPACE pg_default;