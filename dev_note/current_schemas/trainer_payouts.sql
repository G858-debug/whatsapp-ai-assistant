-- SQL for table: trainer_payouts

CREATE TABLE IF NOT EXISTS "trainer_payouts" (
  "create_ddl" text
);

INSERT INTO "trainer_payouts" ("create_ddl") VALUES ('CREATE TABLE public.trainer_payouts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid,
  payout_amount numeric(10,2) NOT NULL,
  status character varying(50) DEFAULT ''pending''::character varying,
  period_start date NOT NULL,
  period_end date NOT NULL,
  total_collected numeric(10,2),
  total_payfast_fees numeric(10,2),
  total_platform_fees numeric(10,2),
  transaction_count integer(32,0),
  bank_name character varying(100) NOT NULL,
  account_holder character varying(255) NOT NULL,
  account_number_masked character varying(50),
  branch_code character varying(10),
  payment_method character varying(50) DEFAULT ''manual_eft''::character varying,
  payment_reference character varying(100),
  paid_at timestamp with time zone,
  payment_proof_url text,
  payment_ids ARRAY,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_37060_11_not_null" CHECK (bank_name IS NOT NULL),
  CONSTRAINT "2200_37060_12_not_null" CHECK (account_holder IS NOT NULL),
  CONSTRAINT "2200_37060_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_37060_3_not_null" CHECK (payout_amount IS NOT NULL),
  CONSTRAINT "2200_37060_5_not_null" CHECK (period_start IS NOT NULL),
  CONSTRAINT "2200_37060_6_not_null" CHECK (period_end IS NOT NULL),
  CONSTRAINT trainer_payouts_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX trainer_payouts_pkey ON public.trainer_payouts USING btree (id)
  CREATE INDEX idx_trainer_payouts_status ON public.trainer_payouts USING btree (status)
  CREATE INDEX idx_trainer_payouts_period ON public.trainer_payouts USING btree (period_start, period_end)');
