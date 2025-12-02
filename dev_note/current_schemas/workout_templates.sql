-- SQL for table: workout_templates

CREATE TABLE IF NOT EXISTS "workout_templates" (
  "create_ddl" text
);

INSERT INTO "workout_templates" ("create_ddl") VALUES ('CREATE TABLE public.workout_templates (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  trainer_id uuid,
  template_name character varying(255) NOT NULL,
  description text,
  workout_type character varying(50),
  exercises jsonb NOT NULL,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_25286_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_25286_3_not_null" CHECK (template_name IS NOT NULL),
  CONSTRAINT "2200_25286_6_not_null" CHECK (exercises IS NOT NULL),
  CONSTRAINT workout_templates_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX workout_templates_pkey ON public.workout_templates USING btree (id)
  CREATE INDEX idx_workout_templates_trainer ON public.workout_templates USING btree (trainer_id)');
