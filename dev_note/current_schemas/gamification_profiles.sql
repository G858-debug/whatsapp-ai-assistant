-- SQL for table: gamification_profiles

CREATE TABLE IF NOT EXISTS "gamification_profiles" (
  "create_ddl" text
);

INSERT INTO "gamification_profiles" ("create_ddl") VALUES ('CREATE TABLE public.gamification_profiles (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid,
  client_id uuid,
  nickname character varying(100),
  points_total integer(32,0) DEFAULT 0,
  is_public boolean DEFAULT false,
  opted_in_global boolean DEFAULT false,
  opted_in_trainer boolean DEFAULT true,
  notification_preferences jsonb DEFAULT ''{"points": true, "challenges": true, "leaderboard": true, "achievements": true}''::jsonb,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_86806_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT check_user_type CHECK ((((trainer_id IS NOT NULL) AND (client_id IS NULL)) OR ((trainer_id IS NULL) AND (client_id IS NOT NULL)))),
  CONSTRAINT gamification_profiles_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id),
  CONSTRAINT gamification_profiles_pkey PRIMARY KEY (id),
  CONSTRAINT gamification_profiles_trainer_id_fkey FOREIGN KEY (trainer_id) REFERENCES public.trainers(id),
  CONSTRAINT unique_client_profile UNIQUE (client_id),
  CONSTRAINT unique_trainer_profile UNIQUE (trainer_id)
);
  CREATE UNIQUE INDEX gamification_profiles_pkey ON public.gamification_profiles USING btree (id)
  CREATE UNIQUE INDEX unique_trainer_profile ON public.gamification_profiles USING btree (trainer_id)
  CREATE UNIQUE INDEX unique_client_profile ON public.gamification_profiles USING btree (client_id)
  CREATE INDEX idx_gamification_profiles_trainer ON public.gamification_profiles USING btree (trainer_id)
  CREATE INDEX idx_gamification_profiles_client ON public.gamification_profiles USING btree (client_id)
  CREATE INDEX idx_gamification_profiles_points ON public.gamification_profiles USING btree (points_total)');
