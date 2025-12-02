-- SQL for table: client_exercise_preferences

CREATE TABLE IF NOT EXISTS "client_exercise_preferences" (
  "create_ddl" text
);

INSERT INTO "client_exercise_preferences" ("create_ddl") VALUES ('CREATE TABLE public.client_exercise_preferences (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  client_id uuid,
  trainer_id uuid,
  muscle_group character varying(50),
  preferred_exercises jsonb,
  avoided_exercises jsonb,
  notes text,
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_25322_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT client_exercise_preferences_client_id_muscle_group_key UNIQUE (client_id, muscle_group),
  CONSTRAINT client_exercise_preferences_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX client_exercise_preferences_pkey ON public.client_exercise_preferences USING btree (id)
  CREATE UNIQUE INDEX client_exercise_preferences_client_id_muscle_group_key ON public.client_exercise_preferences USING btree (client_id, muscle_group)
  CREATE INDEX idx_client_preferences ON public.client_exercise_preferences USING btree (client_id)');
