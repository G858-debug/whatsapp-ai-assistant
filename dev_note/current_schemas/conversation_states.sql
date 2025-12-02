create table public.conversation_states (
  id uuid not null default gen_random_uuid (),
  phone_number character varying(20) not null,
  current_state character varying(50) null default 'idle'::character varying,
  state_data jsonb null default '{}'::jsonb,
  last_activity timestamp with time zone null default now(),
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  context jsonb null default '{}'::jsonb,
  last_intent character varying(50) null,
  session_data jsonb null default '{}'::jsonb,
  state character varying(50) null default 'idle'::character varying,
  role_preference character varying(20) null default null::character varying,
  login_status character varying(20) null default null::character varying,
  current_task_id uuid null,
  constraint conversation_states_pkey primary key (id),
  constraint conversation_states_phone_number_key unique (phone_number)
) TABLESPACE pg_default;

create index IF not exists idx_conversation_states_phone on public.conversation_states using btree (phone_number) TABLESPACE pg_default;

create index IF not exists idx_conversation_states_state on public.conversation_states using btree (current_state) TABLESPACE pg_default;

create index IF not exists idx_conversation_states_activity on public.conversation_states using btree (last_activity) TABLESPACE pg_default;

create index IF not exists idx_conversation_states_context on public.conversation_states using gin (context) TABLESPACE pg_default;

create index IF not exists idx_conversation_states_role_preference on public.conversation_states using btree (role_preference) TABLESPACE pg_default;

create index IF not exists idx_conversation_states_login_status on public.conversation_states using btree (login_status) TABLESPACE pg_default;