-- SQL for table: habit_challenges

CREATE TABLE IF NOT EXISTS "habit_challenges" (
  "create_ddl" text
);

INSERT INTO "habit_challenges" ("create_ddl") VALUES ('CREATE TABLE public.habit_challenges (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid NOT NULL,
  name character varying(100) NOT NULL,
  description text,
  challenge_type character varying(50) NOT NULL,
  target_habit character varying(50) NOT NULL,
  target_value text,
  duration_days integer NOT NULL,
  start_date date NOT NULL,
  end_date date NOT NULL,
  reward character varying(200),
  is_active boolean DEFAULT true,
  participant_count integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "habit_challenges_pkey" PRIMARY KEY (id),
  CONSTRAINT "habit_challenges_trainer_id_fkey" FOREIGN KEY (trainer_id) REFERENCES public.trainers(id),
  CONSTRAINT "habit_challenges_challenge_type_check" CHECK (((challenge_type)::text = ANY ((ARRAY[''consistency''::character varying, ''streak''::character varying, ''competition''::character varying, ''target''::character varying])::text[]))),
  CONSTRAINT "habit_challenges_target_habit_check" CHECK (((target_habit)::text = ANY ((ARRAY[''water_intake''::character varying, ''sleep_hours''::character varying, ''steps''::character varying, ''calories''::character varying, ''workout_completed''::character varying, ''meals_logged''::character varying, ''weight''::character varying, ''mood''::character varying])::text[])))
);
  CREATE UNIQUE INDEX habit_challenges_pkey ON public.habit_challenges USING btree (id)
  CREATE INDEX idx_habit_challenges_trainer ON public.habit_challenges USING btree (trainer_id)
  CREATE INDEX idx_habit_challenges_active ON public.habit_challenges USING btree (is_active)
  CREATE INDEX idx_habit_challenges_dates ON public.habit_challenges USING btree (start_date, end_date)');