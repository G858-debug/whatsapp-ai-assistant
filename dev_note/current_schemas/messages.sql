create table public.messages (
  id uuid not null default gen_random_uuid (),
  trainer_id uuid null,
  client_id uuid null,
  phone_number character varying(20) not null,
  message_text text not null,
  message_type character varying(20) null default 'text'::character varying,
  direction character varying(10) not null,
  processed boolean null default false,
  created_at timestamp with time zone null default now(),
  content text null,
  constraint messages_pkey primary key (id),
  constraint messages_client_id_fkey foreign KEY (client_id) references clients (id),
  constraint messages_trainer_id_fkey foreign KEY (trainer_id) references trainers (id),
  constraint messages_direction_check check (
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
  constraint messages_message_type_check check (
    (
      (message_type)::text = any (
        (
          array[
            'text'::character varying,
            'image'::character varying,
            'audio'::character varying,
            'video'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_messages_phone on public.messages using btree (phone_number) TABLESPACE pg_default;

create index IF not exists idx_messages_trainer on public.messages using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_messages_client on public.messages using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_messages_created on public.messages using btree (created_at) TABLESPACE pg_default;