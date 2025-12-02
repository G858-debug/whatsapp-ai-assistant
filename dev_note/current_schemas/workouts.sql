-- SQL for table: workouts

CREATE TABLE IF NOT EXISTS "workouts" (
  "create_ddl" text
);

INSERT INTO "workouts" ("create_ddl") VALUES ('CREATE TABLE public.workouts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid NOT NULL,
  client_id uuid,
  name character varying(200) NOT NULL,
  description text,
  workout_type character varying(50) DEFAULT ''general''::character varying,
  duration_minutes integer(32,0) DEFAULT 60,
  difficulty_level character varying(20) DEFAULT ''medium''::character varying,
  exercises jsonb DEFAULT ''[]''::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_86753_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_86753_2_not_null" CHECK (trainer_id IS NOT NULL),
  CONSTRAINT "2200_86753_4_not_null" CHECK (name IS NOT NULL),
  CONSTRAINT workouts_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id),
  CONSTRAINT workouts_difficulty_level_check CHECK (((difficulty_level)::text = ANY ((ARRAY[''beginner''::character varying, ''intermediate''::character varying, ''advanced''::character varying])::text[]))),
  CONSTRAINT workouts_pkey PRIMARY KEY (id),
  CONSTRAINT workouts_trainer_id_fkey FOREIGN KEY (trainer_id) REFERENCES public.trainers(id),
  CONSTRAINT workouts_workout_type_check CHECK (((workout_type)::text = ANY ((ARRAY[''strength''::character varying, ''cardio''::character varying, ''flexibility''::character varying, ''general''::character varying])::text[])))
);
  CREATE UNIQUE INDEX workouts_pkey ON public.workouts USING btree (id)
  CREATE INDEX idx_workouts_trainer ON public.workouts USING btree (trainer_id)
  CREATE INDEX idx_workouts_client ON public.workouts USING btree (client_id)
  CREATE INDEX idx_workouts_type ON public.workouts USING btree (workout_type)
  CREATE INDEX idx_workouts_difficulty ON public.workouts USING btree (difficulty_level)');
