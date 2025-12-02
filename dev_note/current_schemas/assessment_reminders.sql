-- SQL for table: assessment_reminders

CREATE TABLE IF NOT EXISTS "assessment_reminders" (
  "create_ddl" text
);

INSERT INTO "assessment_reminders" ("create_ddl") VALUES ('CREATE TABLE public.assessment_reminders (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid,
  client_id uuid,
  template_id uuid,
  due_date timestamp with time zone NOT NULL,
  reminder_type character varying(50),
  sent_at timestamp with time zone,
  status character varying(20) DEFAULT ''pending''::character varying,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_29072_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_29072_5_not_null" CHECK (due_date IS NOT NULL),
  CONSTRAINT assessment_reminders_pkey PRIMARY KEY (id),
  CONSTRAINT assessment_reminders_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.assessment_templates(id)
);
  CREATE UNIQUE INDEX assessment_reminders_pkey ON public.assessment_reminders USING btree (id)
  CREATE INDEX idx_reminders_due ON public.assessment_reminders USING btree (due_date, status)');
