-- SQL for table: rate_limit_violations

CREATE TABLE IF NOT EXISTS "rate_limit_violations" (
  "create_ddl" text
);

INSERT INTO "rate_limit_violations" ("create_ddl") VALUES ('CREATE TABLE public.rate_limit_violations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  phone_number character varying(20) NOT NULL,
  violation_type character varying(50),
  violation_time timestamp with time zone DEFAULT now(),
  ip_address character varying(45),
  message_type character varying(20),
  daily_count integer(32,0),
  tokens_remaining numeric(5,2),
  CONSTRAINT "2200_40068_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_40068_2_not_null" CHECK (phone_number IS NOT NULL),
  CONSTRAINT rate_limit_violations_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX rate_limit_violations_pkey ON public.rate_limit_violations USING btree (id)
  CREATE INDEX idx_violations_phone ON public.rate_limit_violations USING btree (phone_number)
  CREATE INDEX idx_violations_time ON public.rate_limit_violations USING btree (violation_time)');
