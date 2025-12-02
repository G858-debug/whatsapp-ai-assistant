-- SQL for table: workout_history

CREATE TABLE IF NOT EXISTS "workout_history" (
  "create_ddl" text
);

INSERT INTO "workout_history" ("create_ddl") VALUES ('CREATE TABLE public.workout_history (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  client_id uuid,
  trainer_id uuid,
  workout_name character varying(255),
  exercises jsonb NOT NULL,
  sent_at timestamp with time zone DEFAULT now(),
  completed boolean DEFAULT false,
  feedback text,
  CONSTRAINT "2200_25302_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_25302_5_not_null" CHECK (exercises IS NOT NULL),
  CONSTRAINT workout_history_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX workout_history_pkey ON public.workout_history USING btree (id)
  CREATE INDEX idx_workout_history_client ON public.workout_history USING btree (client_id)');
