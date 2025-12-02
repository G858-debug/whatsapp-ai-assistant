create table public.habit_goals (
  id uuid not null default gen_random_uuid (),
  client_id uuid not null,
  habit_type character varying(50) not null,
  goal_value text not null,
  goal_type character varying(20) null default 'daily'::character varying,
  is_active boolean null default true,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint habit_goals_pkey primary key (id),
  constraint habit_goals_client_id_fkey foreign KEY (client_id) references clients (id) on delete CASCADE,
  constraint habit_goals_goal_type_check check (
    (
      (goal_type)::text = any (
        (
          array[
            'daily'::character varying,
            'weekly'::character varying,
            'monthly'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_habit_goals_client on public.habit_goals using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_habit_goals_type on public.habit_goals using btree (habit_type) TABLESPACE pg_default;

create index IF not exists idx_habit_goals_active on public.habit_goals using btree (is_active) TABLESPACE pg_default;

create trigger update_habit_goals_updated_at BEFORE
update on habit_goals for EACH row
execute FUNCTION update_updated_at_column ();