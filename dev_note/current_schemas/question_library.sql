-- SQL for table: question_library

CREATE TABLE IF NOT EXISTS "question_library" (
  "create_ddl" text
);

INSERT INTO "question_library" ("create_ddl") VALUES ('CREATE TABLE public.question_library (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  category character varying(50) NOT NULL,
  subcategory character varying(50),
  question_text text NOT NULL,
  question_type character varying(20),
  field_name character varying(100),
  options jsonb,
  validation_rules jsonb,
  help_text text,
  is_core boolean DEFAULT false,
  display_order integer(32,0),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_29095_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_29095_2_not_null" CHECK (category IS NOT NULL),
  CONSTRAINT "2200_29095_4_not_null" CHECK (question_text IS NOT NULL),
  CONSTRAINT question_library_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX question_library_pkey ON public.question_library USING btree (id)');
