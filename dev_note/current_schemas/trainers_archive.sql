create table public.trainers_archive (
  id uuid not null,
  name character varying(255) null,
  email character varying(255) null,
  whatsapp character varying(20) null,
  business_name character varying(255) null,
  location character varying(255) null,
  specialization character varying(255) null,
  pricing_per_session numeric(10, 2) null,
  status character varying(20) null,
  subscription_status character varying(50) null,
  subscription_expires_at timestamp with time zone null,
  created_at timestamp with time zone null,
  archived_at timestamp with time zone null default now(),
  merge_target_id uuid null,
  archive_reason character varying(50) null,
  constraint trainers_archive_pkey primary key (id)
) TABLESPACE pg_default;