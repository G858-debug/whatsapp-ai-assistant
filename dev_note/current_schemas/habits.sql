-- SQL for table: habits

CREATE TABLE IF NOT EXISTS "habits" (
  "create_ddl" text
);

INSERT INTO "habits" ("create_ddl") VALUES ('CREATE TABLE public.habits (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid NOT NULL,
  client_id uuid,
  habit_type character varying(50) NOT NULL,
  value text NOT NULL,
  date date NOT NULL DEFAULT CURRENT_DATE,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_86611_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_86611_2_not_null" CHECK (trainer_id IS NOT NULL),
  CONSTRAINT "2200_86611_4_not_null" CHECK (habit_type IS NOT NULL),
  CONSTRAINT "2200_86611_5_not_null" CHECK (value IS NOT NULL),
  CONSTRAINT "2200_86611_6_not_null" CHECK (date IS NOT NULL),
  CONSTRAINT habits_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id),
  CONSTRAINT habits_habit_type_check CHECK (((habit_type)::text = ANY ((ARRAY[''water_intake''::character varying, ''sleep_hours''::character varying, ''steps''::character varying, ''calories''::character varying, ''workout_completed''::character varying, ''meals_logged''::character varying, ''weight''::character varying, ''mood''::character varying])::text[]))),
  CONSTRAINT habits_pkey PRIMARY KEY (id),
  CONSTRAINT habits_trainer_id_fkey FOREIGN KEY (trainer_id) REFERENCES public.trainers(id)
);
  CREATE UNIQUE INDEX habits_pkey ON public.habits USING btree (id)
  CREATE INDEX idx_habits_trainer ON public.habits USING btree (trainer_id)
  CREATE INDEX idx_habits_client ON public.habits USING btree (client_id)
  CREATE INDEX idx_habits_date ON public.habits USING btree (date)
  CREATE INDEX idx_habits_type ON public.habits USING btree (habit_type)');
