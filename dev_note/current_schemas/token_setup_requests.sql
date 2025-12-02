-- SQL for table: token_setup_requests

CREATE TABLE IF NOT EXISTS "token_setup_requests" (
  "create_ddl" text
);

INSERT INTO "token_setup_requests" ("create_ddl") VALUES ('CREATE TABLE public.token_setup_requests (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  client_id uuid,
  trainer_id uuid,
  status character varying(50) DEFAULT ''pending''::character varying,
  setup_url text,
  setup_code character varying(20),
  sent_at timestamp with time zone,
  completed_at timestamp with time zone,
  expires_at timestamp with time zone DEFAULT (now() + ''7 days''::interval),
  reminder_sent boolean DEFAULT false,
  token_id uuid,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_37685_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT token_setup_requests_pkey PRIMARY KEY (id),
  CONSTRAINT token_setup_requests_token_id_fkey FOREIGN KEY (token_id) REFERENCES public.client_payment_tokens(id)
);
  CREATE UNIQUE INDEX token_setup_requests_pkey ON public.token_setup_requests USING btree (id)
  CREATE INDEX idx_token_setup_requests_status ON public.token_setup_requests USING btree (status)');
