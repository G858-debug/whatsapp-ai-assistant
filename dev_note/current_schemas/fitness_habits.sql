create table public.fitness_habits (
  id uuid not null default gen_random_uuid (),
  habit_id character varying(10) not null,
  trainer_id character varying(10) not null,
  habit_name character varying(100) not null,
  description text null,
  target_value numeric(10, 2) not null,
  unit character varying(50) not null,
  frequency character varying(20) not null default 'daily'::character varying,
  is_active boolean null default true,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint fitness_habits_pkey primary key (id),
  constraint fitness_habits_habit_id_key unique (habit_id),
  constraint fitness_habits_frequency_check check (
    (
      (frequency)::text = any (
        array[
          ('daily'::character varying)::text,
          ('weekly'::character varying)::text,
          ('monthly'::character varying)::text
        ]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_fitness_habits_trainer on public.fitness_habits using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_fitness_habits_habit_id on public.fitness_habits using btree (habit_id) TABLESPACE pg_default;

create index IF not exists idx_fitness_habits_active on public.fitness_habits using btree (is_active) TABLESPACE pg_default;

create index IF not exists idx_fitness_habits_trainer_active on public.fitness_habits using btree (trainer_id, is_active) TABLESPACE pg_default;

create trigger update_fitness_habits_updated_at BEFORE
update on fitness_habits for EACH row
execute FUNCTION update_updated_at_column ();