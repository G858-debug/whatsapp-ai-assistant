-- SQL for table: assessment_templates

CREATE TABLE IF NOT EXISTS "assessment_templates" (
  "create_ddl" text
);

INSERT INTO "assessment_templates" ("create_ddl") VALUES ('CREATE TABLE public.assessment_templates (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid,
  template_name character varying(255) DEFAULT ''Default Template''::character varying,
  is_active boolean DEFAULT true,
  completed_by character varying(20) DEFAULT ''client''::character varying,
  frequency character varying(20) DEFAULT ''once''::character varying,
  next_due_date timestamp with time zone,
  send_reminders boolean DEFAULT true,
  include_health boolean DEFAULT true,
  include_lifestyle boolean DEFAULT true,
  include_goals boolean DEFAULT true,
  include_measurements boolean DEFAULT true,
  include_tests boolean DEFAULT true,
  include_photos boolean DEFAULT true,
  health_questions jsonb DEFAULT ''[]''::jsonb,
  lifestyle_questions jsonb DEFAULT ''[]''::jsonb,
  goals_questions jsonb DEFAULT ''[]''::jsonb,
  measurement_fields jsonb DEFAULT ''[]''::jsonb,
  test_fields jsonb DEFAULT ''[]''::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_28925_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT assessment_templates_pkey PRIMARY KEY (id),
  CONSTRAINT assessment_templates_trainer_id_template_name_key UNIQUE (trainer_id, template_name)
);
  CREATE UNIQUE INDEX assessment_templates_pkey ON public.assessment_templates USING btree (id)
  CREATE UNIQUE INDEX assessment_templates_trainer_id_template_name_key ON public.assessment_templates USING btree (trainer_id, template_name)
  CREATE INDEX idx_templates_trainer ON public.assessment_templates USING btree (trainer_id)');
