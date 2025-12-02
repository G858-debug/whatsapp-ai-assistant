-- SQL for table: physical_measurements

CREATE TABLE IF NOT EXISTS "physical_measurements" (
  "create_ddl" text
);

INSERT INTO "physical_measurements" ("create_ddl") VALUES ('CREATE TABLE public.physical_measurements (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  assessment_id uuid,
  client_id uuid,
  measurement_date timestamp with time zone DEFAULT now(),
  height_cm numeric(5,2),
  weight_kg numeric(5,2),
  bmi numeric(4,2),
  body_fat_percentage numeric(4,2),
  muscle_mass_kg numeric(5,2),
  neck numeric(5,2),
  chest numeric(5,2),
  waist numeric(5,2),
  hips numeric(5,2),
  upper_arm_left numeric(5,2),
  upper_arm_right numeric(5,2),
  forearm_left numeric(5,2),
  forearm_right numeric(5,2),
  thigh_left numeric(5,2),
  thigh_right numeric(5,2),
  calf_left numeric(5,2),
  calf_right numeric(5,2),
  resting_heart_rate integer(32,0),
  blood_pressure_systolic integer(32,0),
  blood_pressure_diastolic integer(32,0),
  notes text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_29011_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT physical_measurements_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES public.fitness_assessments(id),
  CONSTRAINT physical_measurements_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX physical_measurements_pkey ON public.physical_measurements USING btree (id)');
