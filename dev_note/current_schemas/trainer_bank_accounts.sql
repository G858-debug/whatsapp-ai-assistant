-- SQL for table: trainer_bank_accounts

CREATE TABLE IF NOT EXISTS "trainer_bank_accounts" (
  "create_ddl" text
);

INSERT INTO "trainer_bank_accounts" ("create_ddl") VALUES ('CREATE TABLE public.trainer_bank_accounts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid,
  bank_name character varying(100) NOT NULL,
  account_holder_name character varying(255) NOT NULL,
  account_number character varying(50) NOT NULL,
  account_number_masked character varying(50),
  account_type character varying(50) DEFAULT ''current''::character varying,
  branch_code character varying(10) NOT NULL,
  is_verified boolean DEFAULT false,
  verification_amount numeric(5,2),
  verification_reference character varying(50),
  verified_at timestamp with time zone,
  verification_attempts integer(32,0) DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_37076_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_37076_3_not_null" CHECK (bank_name IS NOT NULL),
  CONSTRAINT "2200_37076_4_not_null" CHECK (account_holder_name IS NOT NULL),
  CONSTRAINT "2200_37076_5_not_null" CHECK (account_number IS NOT NULL),
  CONSTRAINT "2200_37076_8_not_null" CHECK (branch_code IS NOT NULL),
  CONSTRAINT trainer_bank_accounts_pkey PRIMARY KEY (id),
  CONSTRAINT trainer_bank_accounts_trainer_id_key UNIQUE (trainer_id)
);
  CREATE UNIQUE INDEX trainer_bank_accounts_pkey ON public.trainer_bank_accounts USING btree (id)
  CREATE UNIQUE INDEX trainer_bank_accounts_trainer_id_key ON public.trainer_bank_accounts USING btree (trainer_id)');
