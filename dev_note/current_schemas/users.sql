create table public.users (
  id uuid not null default gen_random_uuid (),
  phone_number character varying(20) not null,
  trainer_id character varying(10) null,
  client_id character varying(10) null,
  login_status character varying(20) null default null::character varying,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint users_pkey primary key (id),
  constraint users_phone_number_key unique (phone_number),
  constraint users_login_status_check check (
    (
      (login_status is null)
      or (
        (login_status)::text = any (
          (
            array[
              'trainer'::character varying,
              'client'::character varying
            ]
          )::text[]
        )
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_users_phone_number on public.users using btree (phone_number) TABLESPACE pg_default;

create index IF not exists idx_users_trainer_id on public.users using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_users_client_id on public.users using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_users_login_status on public.users using btree (login_status) TABLESPACE pg_default;