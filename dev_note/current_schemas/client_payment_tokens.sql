-- SQL for table: client_payment_tokens

CREATE TABLE IF NOT EXISTS "client_payment_tokens" (
  "create_ddl" text
);

INSERT INTO "client_payment_tokens" ("create_ddl") VALUES ('CREATE TABLE public.client_payment_tokens (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  trainer_id uuid,
  payfast_token character varying(255) NOT NULL,
  payfast_token_status character varying(50) DEFAULT ''active''::character varying,
  card_last_four character varying(4),
  card_brand character varying(50),
  card_exp_month integer(32,0),
  card_exp_year integer(32,0),
  card_holder_name character varying(255),
  is_default boolean DEFAULT false,
  created_via character varying(50) DEFAULT ''whatsapp''::character varying,
  consent_given boolean DEFAULT true,
  consent_date timestamp with time zone DEFAULT now(),
  consent_message text,
  max_amount_per_transaction numeric(8,2) DEFAULT 5000.00,
  max_transactions_per_month integer(32,0) DEFAULT 10,
  transactions_this_month integer(32,0) DEFAULT 0,
  last_transaction_date timestamp with time zone,
  last_verified_date timestamp with time zone,
  suspended_at timestamp with time zone,
  suspended_reason text,
  deleted_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_37626_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_37626_4_not_null" CHECK (payfast_token IS NOT NULL),
  CONSTRAINT client_payment_tokens_client_id_trainer_id_payfast_token_key UNIQUE (client_id, trainer_id, payfast_token),
  CONSTRAINT client_payment_tokens_payfast_token_key UNIQUE (payfast_token),
  CONSTRAINT client_payment_tokens_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX client_payment_tokens_pkey ON public.client_payment_tokens USING btree (id)
  CREATE UNIQUE INDEX client_payment_tokens_payfast_token_key ON public.client_payment_tokens USING btree (payfast_token)
  CREATE UNIQUE INDEX client_payment_tokens_client_id_trainer_id_payfast_token_key ON public.client_payment_tokens USING btree (client_id, trainer_id, payfast_token)
  CREATE INDEX idx_client_payment_tokens_client ON public.client_payment_tokens USING btree (client_id)
  CREATE INDEX idx_client_payment_tokens_trainer ON public.client_payment_tokens USING btree (trainer_id)
  CREATE INDEX idx_client_payment_tokens_status ON public.client_payment_tokens USING btree (payfast_token_status)');
