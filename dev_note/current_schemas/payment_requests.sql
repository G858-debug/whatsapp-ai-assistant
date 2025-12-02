-- SQL for table: payment_requests

CREATE TABLE IF NOT EXISTS "payment_requests" (
  "create_ddl" text
);

INSERT INTO "payment_requests" ("create_ddl") VALUES ('CREATE TABLE public.payment_requests (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid,
  client_id uuid,
  amount numeric(8,2) NOT NULL,
  description text NOT NULL,
  payment_type character varying(50) DEFAULT ''monthly''::character varying,
  sessions_covered integer(32,0),
  period_start date,
  period_end date,
  status character varying(50) DEFAULT ''pending_trainer''::character varying,
  trainer_approved boolean DEFAULT false,
  trainer_approved_at timestamp with time zone,
  trainer_whatsapp_response text,
  client_approved boolean DEFAULT false,
  client_approved_at timestamp with time zone,
  client_whatsapp_response text,
  payfast_payment_url text,
  payfast_payment_id character varying(255),
  expires_at timestamp with time zone DEFAULT (now() + ''48:00:00''::interval),
  payment_id uuid,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_36999_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_36999_4_not_null" CHECK (amount IS NOT NULL),
  CONSTRAINT "2200_36999_5_not_null" CHECK (description IS NOT NULL),
  CONSTRAINT payment_requests_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id),
  CONSTRAINT payment_requests_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX payment_requests_pkey ON public.payment_requests USING btree (id)
  CREATE INDEX idx_payment_requests_status ON public.payment_requests USING btree (status)
  CREATE INDEX idx_payment_requests_expires ON public.payment_requests USING btree (expires_at)');
