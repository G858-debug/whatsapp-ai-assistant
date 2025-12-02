create table public.clients (
  id uuid not null default gen_random_uuid (),
  trainer_id uuid null,
  name character varying(200) not null,
  whatsapp character varying(20) not null,
  email character varying(255) null,
  status character varying(20) null default 'active'::character varying,
  package_type character varying(50) null default 'single'::character varying,
  sessions_remaining integer null default 1,
  custom_price_per_session numeric(10, 2) null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  fitness_goals text null,
  availability text null,
  current_package character varying(50) null,
  last_session_date date null,
  experience_level character varying(50) null,
  health_conditions text null,
  preferred_training_times text null,
  connection_status character varying(20) null default 'active'::character varying,
  requested_by character varying(20) null default 'client'::character varying,
  invitation_token character varying(255) null,
  invited_at timestamp with time zone null,
  approved_at timestamp with time zone null,
  client_id character varying(10) null,
  constraint clients_pkey primary key (id),
  constraint clients_client_id_key unique (client_id),
  constraint clients_connection_status_check check (
    (
      (connection_status)::text = any (
        (
          array[
            'pending'::character varying,
            'active'::character varying,
            'declined'::character varying,
            'expired'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint clients_package_type_check check (
    (
      (package_type)::text = any (
        (
          array[
            'single'::character varying,
            'package_5'::character varying,
            'package_10'::character varying,
            'package_20'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint clients_requested_by_check check (
    (
      (requested_by)::text = any (
        (
          array[
            'trainer'::character varying,
            'client'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint clients_status_check check (
    (
      (status)::text = any (
        (
          array[
            'active'::character varying,
            'inactive'::character varying,
            'suspended'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_clients_fitness_goals on public.clients using gin (to_tsvector('english'::regconfig, fitness_goals)) TABLESPACE pg_default;

create index IF not exists idx_clients_trainer on public.clients using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_clients_whatsapp on public.clients using btree (whatsapp) TABLESPACE pg_default;

create index IF not exists idx_clients_status on public.clients using btree (status) TABLESPACE pg_default;

create index IF not exists idx_clients_experience_level on public.clients using btree (experience_level) TABLESPACE pg_default;

create index IF not exists idx_clients_connection_status on public.clients using btree (connection_status) TABLESPACE pg_default;

create index IF not exists idx_clients_invitation_token on public.clients using btree (invitation_token) TABLESPACE pg_default;

create index IF not exists idx_clients_trainer_status on public.clients using btree (trainer_id, connection_status) TABLESPACE pg_default;

create unique INDEX IF not exists idx_clients_client_id on public.clients using btree (client_id) TABLESPACE pg_default;