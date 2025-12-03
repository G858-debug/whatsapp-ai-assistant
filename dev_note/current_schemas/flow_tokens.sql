create table public.flow_tokens (
  id uuid not null default gen_random_uuid (),
  phone_number character varying(20) null,
  flow_token character varying(255) not null,
  flow_type character varying(50) not null,
  flow_data jsonb null default '{}'::jsonb,
  status character varying(20) null default 'active'::character varying,
  completed_at timestamp with time zone null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  data jsonb null default '{}'::jsonb,
  token character varying(255) null,
  expires_at timestamp with time zone null,
  user_id text null,
  constraint flow_tokens_pkey primary key (id),
  constraint flow_tokens_flow_token_key unique (flow_token),
  constraint flow_tokens_token_key unique (token),
  constraint flow_tokens_flow_type_check check (
    (
      (flow_type)::text = any (
        (
          array[
            'trainer_onboarding'::character varying,
            'client_onboarding'::character varying,
            'assessment_flow'::character varying,
            'booking_flow'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint flow_tokens_status_check check (
    (
      (status)::text = any (
        (
          array[
            'active'::character varying,
            'completed'::character varying,
            'expired'::character varying,
            'cancelled'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_flow_tokens_phone on public.flow_tokens using btree (phone_number) TABLESPACE pg_default;

create index IF not exists idx_flow_tokens_token on public.flow_tokens using btree (flow_token) TABLESPACE pg_default;

create index IF not exists idx_flow_tokens_type on public.flow_tokens using btree (flow_type) TABLESPACE pg_default;

create index IF not exists idx_flow_tokens_expires_at on public.flow_tokens using btree (expires_at) TABLESPACE pg_default;