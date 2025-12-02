-- SQL for table: habit_streaks

CREATE TABLE IF NOT EXISTS "habit_streaks" (
  "create_ddl" text
);

INSERT INTO "habit_streaks" ("create_ddl") VALUES ('CREATE TABLE public.habit_streaks (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  client_habit_id uuid,
  current_streak integer(32,0) DEFAULT 0,
  longest_streak integer(32,0) DEFAULT 0,
  last_completed_date date,
  streak_broken_date date,
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_42826_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT habit_streaks_client_habit_id_fkey FOREIGN KEY (client_habit_id) REFERENCES public.client_habits(id),
  CONSTRAINT habit_streaks_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX habit_streaks_pkey ON public.habit_streaks USING btree (id)');
