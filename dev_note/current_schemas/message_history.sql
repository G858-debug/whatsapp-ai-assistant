create table public.message_history (
  id uuid not null default gen_random_uuid (),
  phone_number character varying(20) not null,
  message_text text null,
  direction character varying(10) null,
  message_type character varying(20) null default 'text'::character varying,
  processed boolean null default false,
  ai_intent jsonb null default '{}'::jsonb,
  response_data jsonb null default '{}'::jsonb,
  created_at timestamp with time zone null default now(),
  intent character varying(50) null,
  confidence numeric(3, 2) null,
  message text null,
  sender character varying(20) null,
  constraint message_history_pkey primary key (id),
  constraint message_history_direction_check check (
    (
      (direction)::text = any (
        (
          array[
            'inbound'::character varying,
            'outbound'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint message_history_message_type_check check (
    (
      (message_type)::text = any (
        (
          array[
            'text'::character varying,
            'image'::character varying,
            'audio'::character varying,
            'document'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_message_history_phone on public.message_history using btree (phone_number) TABLESPACE pg_default;

create index IF not exists idx_message_history_direction on public.message_history using btree (direction) TABLESPACE pg_default;

create index IF not exists idx_message_history_created on public.message_history using btree (created_at) TABLESPACE pg_default;

create index IF not exists idx_message_history_processed on public.message_history using btree (processed) TABLESPACE pg_default;

create index IF not exists idx_message_history_intent on public.message_history using btree (intent) TABLESPACE pg_default;

create index IF not exists idx_message_history_message on public.message_history using btree (message) TABLESPACE pg_default;

create index IF not exists idx_message_history_sender on public.message_history using btree (sender) TABLESPACE pg_default;