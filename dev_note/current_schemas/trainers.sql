create table public.trainers (
  id uuid not null default gen_random_uuid (),
  name character varying(200) not null,
  whatsapp character varying(20) not null,
  email character varying(255) not null,
  status character varying(20) null default 'active'::character varying,
  pricing_per_session integer null default 500.00,
  subscription_status character varying(50) null default 'free'::character varying,
  subscription_expires_at timestamp with time zone null,
  subscription_end timestamp with time zone null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  flow_token character varying(255) null,
  onboarding_method character varying(20) null default 'chat'::character varying,
  city character varying(100) null,
  specialization text null,
  experience_years character varying(20) null,
  available_days jsonb null default '[]'::jsonb,
  preferred_time_slots character varying(50) null,
  notification_preferences jsonb null default '[]'::jsonb,
  terms_accepted boolean null default false,
  marketing_consent boolean null default false,
  first_name character varying(255) null,
  last_name character varying(255) null,
  business_name character varying(255) null,
  years_experience integer null default 0,
  location character varying(255) null,
  services_offered jsonb null default '[]'::jsonb,
  pricing_flexibility jsonb null default '[]'::jsonb,
  additional_notes text null,
  registration_method character varying(20) null default 'text'::character varying,
  trainer_id character varying(50) null,
  working_hours jsonb null default '{}'::jsonb,
  default_price_per_session integer null,
  sex character varying(20) null,
  birthdate date null,
  specializations_arr jsonb null default '[]'::jsonb,
  constraint trainers_pkey primary key (id),
  constraint trainers_email_key unique (email),
  constraint trainers_trainer_id_key unique (trainer_id),
  constraint trainers_whatsapp_key unique (whatsapp),
  constraint trainers_subscription_status_check check (
    (
      (subscription_status)::text = any (
        (
          array[
            'free'::character varying,
            'premium'::character varying,
            'pro'::character varying,
            'professional'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint trainers_pricing_per_session_check check ((pricing_per_session > 0)),
  constraint trainers_onboarding_method_check check (
    (
      (onboarding_method)::text = any (
        (
          array[
            'chat'::character varying,
            'flow'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint trainers_default_price_per_session_check check ((default_price_per_session > 0)),
  constraint trainers_status_check check (
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

create index IF not exists idx_trainers_onboarding_method on public.trainers using btree (onboarding_method) TABLESPACE pg_default;

create index IF not exists idx_trainers_city on public.trainers using btree (city) TABLESPACE pg_default;

create index IF not exists idx_trainers_whatsapp on public.trainers using btree (whatsapp) TABLESPACE pg_default;

create index IF not exists idx_trainers_email on public.trainers using btree (lower((email)::text)) TABLESPACE pg_default;

create index IF not exists idx_trainers_status on public.trainers using btree (status) TABLESPACE pg_default;

create index IF not exists idx_trainers_flow_token on public.trainers using btree (flow_token) TABLESPACE pg_default;

create index IF not exists idx_trainers_specialization on public.trainers using btree (specialization) TABLESPACE pg_default;

create index IF not exists idx_trainers_services_offered on public.trainers using gin (services_offered jsonb_path_ops) TABLESPACE pg_default;

create index IF not exists idx_trainers_pricing_flexibility on public.trainers using gin (pricing_flexibility jsonb_path_ops) TABLESPACE pg_default;

create index IF not exists idx_trainers_registration_method on public.trainers using btree (registration_method) TABLESPACE pg_default;

create index IF not exists idx_trainers_sex on public.trainers using btree (sex) TABLESPACE pg_default;

create index IF not exists idx_trainers_birthdate on public.trainers using btree (birthdate) TABLESPACE pg_default;

create index IF not exists idx_trainers_specializations_arr on public.trainers using gin (specializations_arr) TABLESPACE pg_default;

create index IF not exists idx_trainers_working_hours on public.trainers using gin (working_hours) TABLESPACE pg_default;

create unique INDEX IF not exists idx_trainers_trainer_id on public.trainers using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_trainers_default_price on public.trainers using btree (default_price_per_session) TABLESPACE pg_default
where
  (default_price_per_session is not null);

create trigger update_trainers_updated_at BEFORE
update on trainers for EACH row
execute FUNCTION update_updated_at_column ();

create trigger auto_sync_trainer_id BEFORE INSERT
or
update on trainers for EACH row
execute FUNCTION sync_trainer_id ();