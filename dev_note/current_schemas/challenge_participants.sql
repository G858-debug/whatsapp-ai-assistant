create table public.challenge_participants (
  id uuid not null default gen_random_uuid (),
  challenge_id uuid not null,
  client_id uuid not null,
  joined_at timestamp with time zone null default now(),
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  current_score integer null default 0,
  completion_percentage numeric(5, 2) null default 0.00,
  is_active boolean null default true,
  completed_at timestamp with time zone null,
  constraint challenge_participants_pkey primary key (id),
  constraint unique_challenge_participant unique (challenge_id, client_id),
  constraint challenge_participants_challenge_id_fkey foreign KEY (challenge_id) references habit_challenges (id) on delete CASCADE,
  constraint challenge_participants_client_id_fkey foreign KEY (client_id) references clients (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_challenge_participants_challenge on public.challenge_participants using btree (challenge_id) TABLESPACE pg_default;

create index IF not exists idx_challenge_participants_client on public.challenge_participants using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_challenge_participants_active on public.challenge_participants using btree (is_active) TABLESPACE pg_default;