create table public.client_trainer_list (
  id uuid not null default gen_random_uuid (),
  client_id character varying(10) not null,
  trainer_id character varying(10) not null,
  connection_status character varying(20) null default 'active'::character varying,
  invited_by character varying(20) null default 'client'::character varying,
  invitation_token character varying(255) null,
  invited_at timestamp with time zone null,
  approved_at timestamp with time zone null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint client_trainer_list_pkey primary key (id),
  constraint client_trainer_list_unique unique (client_id, trainer_id),
  constraint client_trainer_list_invited_by_check check (
    (
      (invited_by)::text = any (
        (
          array[
            'trainer'::character varying,
            'client'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint client_trainer_list_status_check check (
    (
      (connection_status)::text = any (
        (
          array[
            'pending'::character varying,
            'active'::character varying,
            'declined'::character varying,
            'removed'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_client_trainer_list_client on public.client_trainer_list using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_client_trainer_list_trainer on public.client_trainer_list using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_client_trainer_list_status on public.client_trainer_list using btree (connection_status) TABLESPACE pg_default;

create index IF not exists idx_client_trainer_list_token on public.client_trainer_list using btree (invitation_token) TABLESPACE pg_default;