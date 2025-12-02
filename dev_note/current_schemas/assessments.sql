-- SQL for table: assessments

CREATE TABLE IF NOT EXISTS "assessments" (
  "create_ddl" text
);

INSERT INTO "assessments" ("create_ddl") VALUES ('CREATE TABLE public.assessments (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid NOT NULL,
  assessment_type character varying(50) NOT NULL,
  questions jsonb NOT NULL DEFAULT ''{}''::jsonb,
  answers jsonb NOT NULL DEFAULT ''{}''::jsonb,
  score numeric(5,2),
  completed_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_86675_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_86675_2_not_null" CHECK (client_id IS NOT NULL),
  CONSTRAINT "2200_86675_3_not_null" CHECK (assessment_type IS NOT NULL),
  CONSTRAINT "2200_86675_4_not_null" CHECK (questions IS NOT NULL),
  CONSTRAINT "2200_86675_5_not_null" CHECK (answers IS NOT NULL),
  CONSTRAINT assessments_assessment_type_check CHECK (((assessment_type)::text = ANY ((ARRAY[''initial''::character varying, ''progress''::character varying, ''final''::character varying])::text[]))),
  CONSTRAINT assessments_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id),
  CONSTRAINT assessments_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX assessments_pkey ON public.assessments USING btree (id)
  CREATE INDEX idx_assessments_type ON public.assessments USING btree (assessment_type)
  CREATE INDEX idx_assessments_completed ON public.assessments USING btree (completed_at)');
