-- SQL for table: challenge_progress

CREATE TABLE IF NOT EXISTS "challenge_progress" (
  "create_ddl" text
);

INSERT INTO "challenge_progress" ("create_ddl") VALUES ('CREATE TABLE public.challenge_progress (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  participant_id uuid NOT NULL,
  challenge_id uuid NOT NULL,
  date date NOT NULL DEFAULT CURRENT_DATE,
  value_achieved numeric(10,2) NOT NULL DEFAULT 0,
  points_earned integer(32,0) DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_86876_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_86876_2_not_null" CHECK (participant_id IS NOT NULL),
  CONSTRAINT "2200_86876_3_not_null" CHECK (challenge_id IS NOT NULL),
  CONSTRAINT "2200_86876_4_not_null" CHECK (date IS NOT NULL),
  CONSTRAINT "2200_86876_5_not_null" CHECK (value_achieved IS NOT NULL),
  CONSTRAINT challenge_progress_challenge_id_fkey FOREIGN KEY (challenge_id) REFERENCES public.challenges(id),
  CONSTRAINT challenge_progress_participant_id_fkey FOREIGN KEY (participant_id) REFERENCES public.challenge_participants(id),
  CONSTRAINT challenge_progress_pkey PRIMARY KEY (id),
  CONSTRAINT unique_progress_per_day UNIQUE (participant_id, date)
);
  CREATE UNIQUE INDEX challenge_progress_pkey ON public.challenge_progress USING btree (id)
  CREATE UNIQUE INDEX unique_progress_per_day ON public.challenge_progress USING btree (participant_id, date)
  CREATE INDEX idx_challenge_progress_participant ON public.challenge_progress USING btree (participant_id)
  CREATE INDEX idx_challenge_progress_challenge ON public.challenge_progress USING btree (challenge_id)
  CREATE INDEX idx_challenge_progress_date ON public.challenge_progress USING btree (date)');
