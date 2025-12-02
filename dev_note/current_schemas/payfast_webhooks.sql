-- SQL for table: payfast_webhooks

CREATE TABLE IF NOT EXISTS "payfast_webhooks" (
  "create_ddl" text
);

INSERT INTO "payfast_webhooks" ("create_ddl") VALUES ('CREATE TABLE public.payfast_webhooks (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  webhook_type character varying(50),
  event_type character varying(50),
  payfast_payment_id character varying(255),
  payfast_pf_payment_id character varying(255),
  payfast_token character varying(255),
  trainer_id uuid,
  client_id uuid,
  payment_id uuid,
  subscription_id uuid,
  headers jsonb,
  payload jsonb,
  signature character varying(255),
  signature_valid boolean,
  processed boolean DEFAULT false,
  processed_at timestamp with time zone,
  error_message text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_37096_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT payfast_webhooks_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id),
  CONSTRAINT payfast_webhooks_pkey PRIMARY KEY (id),
  CONSTRAINT payfast_webhooks_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.trainer_subscriptions(id)
);
  CREATE UNIQUE INDEX payfast_webhooks_pkey ON public.payfast_webhooks USING btree (id)
  CREATE INDEX idx_payfast_webhooks_payment_id ON public.payfast_webhooks USING btree (payfast_payment_id)
  CREATE INDEX idx_payfast_webhooks_token ON public.payfast_webhooks USING btree (payfast_token)');
