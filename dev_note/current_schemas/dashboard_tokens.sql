create table public.dashboard_tokens (
  id uuid not null default gen_random_uuid (),
  user_id text not null,
  role text not null,
  purpose text not null default 'dashboard'::text,
  token_hash text not null,
  expires_at timestamp with time zone not null,
  created_at timestamp with time zone null default now(),
  used boolean null default false,
  used_at timestamp with time zone null,
  constraint dashboard_tokens_pkey1 primary key (id),
  constraint dashboard_tokens_token_hash_key unique (token_hash),
  constraint dashboard_tokens_role_check check (
    (
      role = any (array['trainer'::text, 'client'::text])
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_dashboard_tokens_user_id on public.dashboard_tokens using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_dashboard_tokens_token_hash on public.dashboard_tokens using btree (token_hash) TABLESPACE pg_default;

create index IF not exists idx_dashboard_tokens_expires_at on public.dashboard_tokens using btree (expires_at) TABLESPACE pg_default;