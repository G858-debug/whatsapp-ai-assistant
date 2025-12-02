create table public.trainer_client_list (
  id uuid not null default gen_random_uuid (),
  trainer_id character varying(10) not null,
  client_id character varying(10) not null,
  connection_status character varying(20) null default 'active'::character varying,
  invited_by character varying(20) null default 'trainer'::character varying,
  invitation_token character varying(255) null,
  invited_at timestamp with time zone null,
  approved_at timestamp with time zone null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint trainer_client_list_pkey primary key (id),
  constraint trainer_client_list_unique unique (trainer_id, client_id),
  constraint trainer_client_list_invited_by_check check (
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
  constraint trainer_client_list_status_check check (
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

create index IF not exists idx_trainer_client_list_trainer on public.trainer_client_list using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_trainer_client_list_client on public.trainer_client_list using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_trainer_client_list_status on public.trainer_client_list using btree (connection_status) TABLESPACE pg_default;

create index IF not exists idx_trainer_client_list_token on public.trainer_client_list using btree (invitation_token) TABLESPACE pg_default;