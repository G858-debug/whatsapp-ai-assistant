-- SQL for table: fitness_test_results

CREATE TABLE IF NOT EXISTS "fitness_test_results" (
  "create_ddl" text
);

INSERT INTO "fitness_test_results" ("create_ddl") VALUES ('CREATE TABLE public.fitness_test_results (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  assessment_id uuid,
  client_id uuid,
  test_date timestamp with time zone DEFAULT now(),
  cardio_test_type character varying(50),
  cardio_test_result text,
  estimated_vo2_max numeric(5,2),
  sit_and_reach_cm numeric(5,2),
  shoulder_flexibility_left character varying(20),
  shoulder_flexibility_right character varying(20),
  push_ups_count integer(32,0),
  push_ups_type character varying(20),
  plank_hold_seconds integer(32,0),
  squat_assessment character varying(20),
  squat_reps integer(32,0),
  squat_notes text,
  single_leg_stand_left_seconds integer(32,0),
  single_leg_stand_right_seconds integer(32,0),
  balance_notes text,
  posture_assessment jsonb,
  movement_imbalances ARRAY,
  movement_notes text,
  other_tests jsonb,
  trainer_observations text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_29052_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT fitness_test_results_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES public.fitness_assessments(id),
  CONSTRAINT fitness_test_results_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX fitness_test_results_pkey ON public.fitness_test_results USING btree (id)');
