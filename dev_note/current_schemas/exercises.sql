-- SQL for table: exercises

CREATE TABLE IF NOT EXISTS "exercises" (
  "create_ddl" text
);

INSERT INTO "exercises" ("create_ddl") VALUES ('CREATE TABLE public.exercises (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  name character varying(255) NOT NULL,
  muscle_group character varying(50) NOT NULL,
  gif_url_male text,
  gif_url_female text,
  instructions text,
  equipment character varying(100),
  difficulty character varying(20) DEFAULT ''intermediate''::character varying,
  created_at timestamp with time zone DEFAULT now(),
  category character varying(100),
  muscle_groups ARRAY,
  gif_url_neutral character varying(500),
  form_tips ARRAY,
  common_mistakes ARRAY,
  updated_at timestamp with time zone DEFAULT now(),
  is_active boolean DEFAULT true,
  alternate_names ARRAY,
  CONSTRAINT "2200_25274_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_25274_2_not_null" CHECK (name IS NOT NULL),
  CONSTRAINT "2200_25274_3_not_null" CHECK (muscle_group IS NOT NULL),
  CONSTRAINT exercises_name_key UNIQUE (name),
  CONSTRAINT exercises_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX exercises_pkey ON public.exercises USING btree (id)
  CREATE UNIQUE INDEX exercises_name_key ON public.exercises USING btree (name)
  CREATE INDEX idx_exercises_muscle_group ON public.exercises USING btree (muscle_group)
  CREATE INDEX idx_exercise_name ON public.exercises USING btree (name)
  CREATE INDEX idx_exercise_category ON public.exercises USING btree (category)
  CREATE INDEX idx_exercise_active ON public.exercises USING btree (is_active)');
