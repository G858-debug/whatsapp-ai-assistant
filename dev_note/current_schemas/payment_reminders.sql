-- SQL for table: payment_reminders

CREATE TABLE IF NOT EXISTS "payment_reminders" (
  "create_ddl" text
);

INSERT INTO "payment_reminders" ("create_ddl") VALUES ('CREATE TABLE public.payment_reminders (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  trainer_id uuid,
  reminder_day integer(32,0) NOT NULL,
  reminder_enabled boolean DEFAULT true,
  last_sent_date date,
  next_scheduled_date date,
  total_clients integer(32,0) DEFAULT 0,
  clients_to_bill integer(32,0) DEFAULT 0,
  reminder_sent_at timestamp with time zone,
  trainer_response text,
  payment_requests_created integer(32,0) DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_37038_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_37038_3_not_null" CHECK (reminder_day IS NOT NULL),
  CONSTRAINT payment_reminders_pkey PRIMARY KEY (id),
  CONSTRAINT payment_reminders_reminder_day_check CHECK (((reminder_day >= 1) AND (reminder_day <= 28))),
  CONSTRAINT payment_reminders_trainer_id_key UNIQUE (trainer_id)
);
  CREATE UNIQUE INDEX payment_reminders_pkey ON public.payment_reminders USING btree (id)
  CREATE UNIQUE INDEX payment_reminders_trainer_id_key ON public.payment_reminders USING btree (trainer_id)');
