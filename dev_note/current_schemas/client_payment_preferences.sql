-- SQL for table: client_payment_preferences

CREATE TABLE IF NOT EXISTS "client_payment_preferences" (
  "create_ddl" text
);

INSERT INTO "client_payment_preferences" ("create_ddl") VALUES ('CREATE TABLE public.client_payment_preferences (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  trainer_id uuid,
  preferred_payment_day integer(32,0),
  auto_approve_enabled boolean DEFAULT false,
  auto_approve_max_amount numeric(8,2) DEFAULT 1000.00,
  require_itemized_invoice boolean DEFAULT true,
  send_payment_reminders boolean DEFAULT true,
  reminder_days_before integer(32,0) DEFAULT 2,
  send_payment_receipts boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_37658_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT client_payment_preferences_client_id_trainer_id_key UNIQUE (client_id, trainer_id),
  CONSTRAINT client_payment_preferences_pkey PRIMARY KEY (id),
  CONSTRAINT client_payment_preferences_preferred_payment_day_check CHECK (((preferred_payment_day >= 1) AND (preferred_payment_day <= 28)))
);
  CREATE UNIQUE INDEX client_payment_preferences_pkey ON public.client_payment_preferences USING btree (id)
  CREATE UNIQUE INDEX client_payment_preferences_client_id_trainer_id_key ON public.client_payment_preferences USING btree (client_id, trainer_id)');
