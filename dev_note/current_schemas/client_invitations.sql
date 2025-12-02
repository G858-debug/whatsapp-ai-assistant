create table public.client_invitations (
  id uuid not null default gen_random_uuid (),
  trainer_id uuid not null,
  client_phone character varying(20) not null,
  client_name character varying(255) null,
  client_email character varying(255) null,
  invitation_token character varying(255) not null,
  invitation_method character varying(20) null default 'whatsapp'::character varying,
  status character varying(20) null default 'pending'::character varying,
  message text null,
  expires_at timestamp with time zone null default (now() + '7 days'::interval),
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  prefilled_data jsonb null,
  constraint client_invitations_pkey primary key (id),
  constraint client_invitations_invitation_token_key unique (invitation_token),
  constraint unique_trainer_client_invitation unique (trainer_id, client_phone),
  constraint client_invitations_trainer_id_fkey foreign KEY (trainer_id) references trainers (id) on delete CASCADE,
  constraint client_invitations_status_check check (
    (
      (status)::text = any (
        (
          array[
            'pending'::character varying,
            'accepted'::character varying,
            'declined'::character varying,
            'expired'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_client_invitations_trainer on public.client_invitations using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_client_invitations_status on public.client_invitations using btree (status) TABLESPACE pg_default;

create index IF not exists idx_client_invitations_token on public.client_invitations using btree (invitation_token) TABLESPACE pg_default;

create index IF not exists idx_client_invitations_expires on public.client_invitations using btree (expires_at) TABLESPACE pg_default;

create index IF not exists idx_client_invitations_prefilled_data on public.client_invitations using gin (prefilled_data) TABLESPACE pg_default;