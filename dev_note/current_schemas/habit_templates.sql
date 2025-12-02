-- SQL for table: habit_templates

CREATE TABLE IF NOT EXISTS "habit_templates" (
  "create_ddl" text
);

INSERT INTO "habit_templates" ("create_ddl") VALUES ('CREATE TABLE public.habit_templates (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid,
  name character varying(100) NOT NULL,
  category character varying(50),
  description text,
  emoji character varying(10),
  measurement_type character varying(20),
  target_value integer(32,0),
  unit character varying(20),
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_42696_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_42696_3_not_null" CHECK (name IS NOT NULL),
  CONSTRAINT habit_templates_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX habit_templates_pkey ON public.habit_templates USING btree (id)');
