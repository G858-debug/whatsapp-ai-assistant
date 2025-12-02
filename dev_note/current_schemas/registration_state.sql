-- SQL for table: registration_state

CREATE TABLE IF NOT EXISTS "registration_state" (
  "create_ddl" text
);

INSERT INTO "registration_state" ("create_ddl") VALUES ('CREATE TABLE public.registration_state (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  phone character varying(20) NOT NULL,
  user_type character varying(20),
  step character varying(50) NOT NULL,
  data jsonb DEFAULT ''{}''::jsonb,
  expires_at timestamp with time zone DEFAULT (now() + ''01:00:00''::interval),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_66402_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_66402_2_not_null" CHECK (phone IS NOT NULL),
  CONSTRAINT "2200_66402_4_not_null" CHECK (step IS NOT NULL),
  CONSTRAINT registration_state_phone_key UNIQUE (phone),
  CONSTRAINT registration_state_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX registration_state_pkey ON public.registration_state USING btree (id)
  CREATE UNIQUE INDEX registration_state_phone_key ON public.registration_state USING btree (phone)
  CREATE INDEX idx_registration_state_phone ON public.registration_state USING btree (phone)
  CREATE INDEX idx_registration_state_expires ON public.registration_state USING btree (expires_at)');
