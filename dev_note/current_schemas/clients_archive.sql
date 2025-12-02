create table public.clients_archive (
  id uuid not null,
  trainer_id uuid null,
  name character varying(255) null,
  email character varying(255) null,
  whatsapp character varying(20) null,
  fitness_goals text null,
  availability text null,
  sessions_remaining integer null,
  package_type character varying(50) null,
  custom_price_per_session numeric(10, 2) null,
  status character varying(20) null,
  created_at timestamp with time zone null,
  archived_at timestamp with time zone null default now(),
  merge_target_id uuid null,
  archive_reason character varying(50) null,
  constraint clients_archive_pkey primary key (id)
) TABLESPACE pg_default;