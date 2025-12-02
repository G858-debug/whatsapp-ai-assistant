-- SQL for table: challenges

CREATE TABLE IF NOT EXISTS "challenges" (
  "create_ddl" text
);

INSERT INTO "challenges" ("create_ddl") VALUES ('CREATE TABLE public.challenges (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  created_by uuid,
  name character varying(200) NOT NULL,
  description text,
  type character varying(50) NOT NULL,
  start_date date NOT NULL,
  end_date date NOT NULL,
  target_value numeric(10,2),
  points_reward integer(32,0) NOT NULL DEFAULT 100,
  is_active boolean DEFAULT true,
  max_participants integer(32,0),
  challenge_rules jsonb DEFAULT ''{}''::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_86836_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_86836_3_not_null" CHECK (name IS NOT NULL),
  CONSTRAINT "2200_86836_5_not_null" CHECK (type IS NOT NULL),
  CONSTRAINT "2200_86836_6_not_null" CHECK (start_date IS NOT NULL),
  CONSTRAINT "2200_86836_7_not_null" CHECK (end_date IS NOT NULL),
  CONSTRAINT "2200_86836_9_not_null" CHECK (points_reward IS NOT NULL),
  CONSTRAINT challenges_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.trainers(id),
  CONSTRAINT challenges_pkey PRIMARY KEY (id),
  CONSTRAINT check_dates CHECK ((end_date > start_date)),
  CONSTRAINT check_max_participants CHECK (((max_participants IS NULL) OR (max_participants > 0))),
  CONSTRAINT check_points_positive CHECK ((points_reward > 0))
);
  CREATE UNIQUE INDEX challenges_pkey ON public.challenges USING btree (id)
  CREATE INDEX idx_challenges_created_by ON public.challenges USING btree (created_by)
  CREATE INDEX idx_challenges_dates ON public.challenges USING btree (start_date, end_date)
  CREATE INDEX idx_challenges_active ON public.challenges USING btree (is_active)');
