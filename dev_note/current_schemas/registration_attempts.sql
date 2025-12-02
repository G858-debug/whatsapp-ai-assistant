create table public.registration_attempts (
  id uuid not null default gen_random_uuid (),
  phone character varying(20) not null,
  user_type character varying(20) null,
  existing_user_id uuid null,
  attempt_type character varying(50) null,
  attempt_data jsonb null default '{}'::jsonb,
  ip_address inet null,
  user_agent text null,
  created_at timestamp with time zone null default now(),
  constraint registration_attempts_pkey primary key (id),
  constraint registration_attempts_attempt_type_check check (
    (
      (attempt_type)::text = any (
        (
          array[
            'new'::character varying,
            'duplicate'::character varying,
            'retry'::character varying,
            'abandoned'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint registration_attempts_user_type_check check (
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

create index IF not exists idx_registration_attempts_phone on public.registration_attempts using btree (phone) TABLESPACE pg_default;

create index IF not exists idx_registration_attempts_user on public.registration_attempts using btree (existing_user_id) TABLESPACE pg_default;

create index IF not exists idx_registration_attempts_created on public.registration_attempts using btree (created_at) TABLESPACE pg_default;