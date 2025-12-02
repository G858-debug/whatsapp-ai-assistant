-- SQL for table: payment_audit_log

CREATE TABLE IF NOT EXISTS "payment_audit_log" (
  "create_ddl" text
);

INSERT INTO "payment_audit_log" ("create_ddl") VALUES ('CREATE TABLE public.payment_audit_log (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid,
  client_id uuid,
  payment_id uuid,
  payment_request_id uuid,
  payout_id uuid,
  action character varying(100) NOT NULL,
  action_by character varying(50),
  amount numeric(10,2),
  description text,
  whatsapp_number character varying(20),
  whatsapp_message text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_37126_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_37126_7_not_null" CHECK (action IS NOT NULL),
  CONSTRAINT payment_audit_log_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id),
  CONSTRAINT payment_audit_log_payment_request_id_fkey FOREIGN KEY (payment_request_id) REFERENCES public.payment_requests(id),
  CONSTRAINT payment_audit_log_payout_id_fkey FOREIGN KEY (payout_id) REFERENCES public.trainer_payouts(id),
  CONSTRAINT payment_audit_log_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX payment_audit_log_pkey ON public.payment_audit_log USING btree (id)
  CREATE INDEX idx_payment_audit_log_created ON public.payment_audit_log USING btree (created_at)');
