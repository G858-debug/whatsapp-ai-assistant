create table public.registration_sessions (
  id uuid not null default gen_random_uuid (),
  phone character varying(20) not null,
  user_type character varying(20) not null,
  registration_type character varying(20) not null,
  step character varying(50) not null,
  status character varying(20) null default 'active'::character varying,
  data jsonb null default '{}'::jsonb,
  retry_count integer null default 0,
  needs_retry boolean null default false,
  last_error_at timestamp with time zone null,
  completed_at timestamp with time zone null,
  expires_at timestamp with time zone null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint registration_sessions_pkey primary key (id),
  constraint registration_sessions_registration_type_check check (
    (
      (registration_type)::text = any (
        (
          array[
            'trainer'::character varying,
            'client'::character varying,
            'unknown'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint registration_sessions_status_check check (
    (
      (status)::text = any (
        (
          array[
            'active'::character varying,
            'in_progress'::character varying,
            'completed'::character varying,
            'expired'::character varying,
            'cancelled'::character varying,
            'abandoned'::character varying,
            'error'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint registration_sessions_user_type_check check (
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

create index IF not exists idx_registration_sessions_phone on public.registration_sessions using btree (phone) TABLESPACE pg_default;

create index IF not exists idx_registration_sessions_status on public.registration_sessions using btree (status) TABLESPACE pg_default;

create index IF not exists idx_registration_sessions_expires on public.registration_sessions using btree (expires_at) TABLESPACE pg_default;

create index IF not exists idx_registration_sessions_needs_retry on public.registration_sessions using btree (needs_retry) TABLESPACE pg_default
where
  (needs_retry = true);

create trigger update_registration_sessions_updated_at BEFORE
update on registration_sessions for EACH row
execute FUNCTION update_updated_at_column ();