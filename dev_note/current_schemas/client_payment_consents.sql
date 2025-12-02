-- SQL for table: client_payment_consents

CREATE TABLE IF NOT EXISTS "client_payment_consents" (
  "create_ddl" text
);

INSERT INTO "client_payment_consents" ("create_ddl") VALUES ('CREATE TABLE public.client_payment_consents (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  trainer_id uuid,
  consent_given boolean DEFAULT false,
  consent_date timestamp with time zone,
  consent_whatsapp_message text,
  preferred_payment_method character varying(50) DEFAULT ''payfast''::character varying,
  preferred_payment_day integer(32,0),
  auto_approve_payments boolean DEFAULT false,
  max_auto_approve_amount numeric(8,2) DEFAULT 1000.00,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_36972_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT client_payment_consents_client_id_trainer_id_key UNIQUE (client_id, trainer_id),
  CONSTRAINT client_payment_consents_pkey PRIMARY KEY (id),
  CONSTRAINT client_payment_consents_preferred_payment_day_check CHECK (((preferred_payment_day >= 1) AND (preferred_payment_day <= 28)))
);
  CREATE UNIQUE INDEX client_payment_consents_pkey ON public.client_payment_consents USING btree (id)
  CREATE UNIQUE INDEX client_payment_consents_client_id_trainer_id_key ON public.client_payment_consents USING btree (client_id, trainer_id)');
