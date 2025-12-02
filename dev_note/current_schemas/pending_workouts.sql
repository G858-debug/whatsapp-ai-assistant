-- SQL for table: pending_workouts

CREATE TABLE IF NOT EXISTS "pending_workouts" (
  "create_ddl" text
);

INSERT INTO "pending_workouts" ("create_ddl") VALUES ('CREATE TABLE public.pending_workouts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid NOT NULL,
  client_id uuid NOT NULL,
  client_name character varying(255),
  client_whatsapp character varying(50),
  workout_message text,
  exercises json,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_27655_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_27655_2_not_null" CHECK (trainer_id IS NOT NULL),
  CONSTRAINT "2200_27655_3_not_null" CHECK (client_id IS NOT NULL),
  CONSTRAINT pending_workouts_pkey PRIMARY KEY (id),
  CONSTRAINT unique_trainer_pending UNIQUE (trainer_id)
);
  CREATE UNIQUE INDEX pending_workouts_pkey ON public.pending_workouts USING btree (id)
  CREATE UNIQUE INDEX unique_trainer_pending ON public.pending_workouts USING btree (trainer_id)
  CREATE INDEX idx_pending_trainer ON public.pending_workouts USING btree (trainer_id)');
