-- SQL for table: subscription_payment_history

CREATE TABLE IF NOT EXISTS "subscription_payment_history" (
  "create_ddl" text
);

INSERT INTO "subscription_payment_history" ("create_ddl") VALUES ('CREATE TABLE public.subscription_payment_history (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid,
  subscription_id uuid,
  amount numeric(8,2) NOT NULL,
  fee_amount numeric(8,2) DEFAULT 0,
  net_amount numeric(8,2),
  payment_date timestamp with time zone DEFAULT now(),
  payment_status character varying(50) DEFAULT ''pending''::character varying,
  payfast_payment_id character varying(255),
  payfast_pf_payment_id character varying(255),
  payfast_payment_status character varying(50),
  payfast_item_name character varying(255),
  payfast_signature character varying(255),
  webhook_data jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_36948_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_36948_4_not_null" CHECK (amount IS NOT NULL),
  CONSTRAINT subscription_payment_history_payfast_payment_id_key UNIQUE (payfast_payment_id),
  CONSTRAINT subscription_payment_history_pkey PRIMARY KEY (id),
  CONSTRAINT subscription_payment_history_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.trainer_subscriptions(id)
);
  CREATE UNIQUE INDEX subscription_payment_history_pkey ON public.subscription_payment_history USING btree (id)
  CREATE UNIQUE INDEX subscription_payment_history_payfast_payment_id_key ON public.subscription_payment_history USING btree (payfast_payment_id)
  CREATE INDEX idx_subscription_payment_history_trainer ON public.subscription_payment_history USING btree (trainer_id)');
