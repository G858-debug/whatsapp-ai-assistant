-- SQL for table: fitness_goals

CREATE TABLE IF NOT EXISTS "fitness_goals" (
  "create_ddl" text
);

INSERT INTO "fitness_goals" ("create_ddl") VALUES ('CREATE TABLE public.fitness_goals (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  assessment_id uuid,
  client_id uuid,
  primary_goal character varying(50),
  goal_description text,
  specific_targets jsonb,
  timeline_weeks integer(32,0),
  previous_experience text,
  preferred_training_style ARRAY,
  exercise_likes ARRAY,
  exercise_dislikes ARRAY,
  motivation_level integer(32,0),
  success_factors text,
  failure_factors text,
  support_system text,
  confidence_level integer(32,0),
  concerns text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_29031_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT fitness_goals_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES public.fitness_assessments(id),
  CONSTRAINT fitness_goals_confidence_level_check CHECK (((confidence_level IS NULL) OR ((confidence_level >= 1) AND (confidence_level <= 10)))),
  CONSTRAINT fitness_goals_motivation_level_check CHECK (((motivation_level IS NULL) OR ((motivation_level >= 1) AND (motivation_level <= 10)))),
  CONSTRAINT fitness_goals_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX fitness_goals_pkey ON public.fitness_goals USING btree (id)');
