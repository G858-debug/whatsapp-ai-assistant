-- SQL for table: client_habits

CREATE TABLE IF NOT EXISTS "client_habits" (
  "create_ddl" text
);

INSERT INTO "client_habits" ("create_ddl") VALUES ('CREATE TABLE public.client_habits (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  trainer_id uuid,
  template_id uuid,
  custom_name character varying(100),
  target_value integer(32,0),
  frequency character varying(20) DEFAULT ''daily''::character varying,
  reminder_time time without time zone,
  is_active boolean DEFAULT true,
  start_date date DEFAULT CURRENT_DATE,
  end_date date,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_42734_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT client_habits_pkey PRIMARY KEY (id),
  CONSTRAINT client_habits_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.habit_templates(id)
);
  CREATE UNIQUE INDEX client_habits_pkey ON public.client_habits USING btree (id)');
