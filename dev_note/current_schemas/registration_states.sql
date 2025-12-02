-- SQL for table: registration_states

CREATE TABLE IF NOT EXISTS "registration_states" (
  "create_ddl" text
);

INSERT INTO "registration_states" ("create_ddl") VALUES ('CREATE TABLE public.registration_states (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  phone_number character varying(20) NOT NULL,
  user_type character varying(20) NOT NULL,
  current_step integer(32,0) DEFAULT 0,
  data jsonb DEFAULT ''{}''::jsonb,
  completed boolean DEFAULT false,
  completed_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_71008_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_71008_2_not_null" CHECK (phone_number IS NOT NULL),
  CONSTRAINT "2200_71008_3_not_null" CHECK (user_type IS NOT NULL),
  CONSTRAINT registration_states_pkey PRIMARY KEY (id),
  CONSTRAINT registration_states_user_type_check CHECK (((user_type)::text = ANY ((ARRAY[''trainer''::character varying, ''client''::character varying])::text[])))
);
  CREATE UNIQUE INDEX registration_states_pkey ON public.registration_states USING btree (id)
  CREATE INDEX idx_registration_states_phone ON public.registration_states USING btree (phone_number)
  CREATE INDEX idx_registration_states_completed ON public.registration_states USING btree (completed)');
