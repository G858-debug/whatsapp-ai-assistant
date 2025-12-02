-- SQL for table: rate_limit_blocks

CREATE TABLE IF NOT EXISTS "rate_limit_blocks" (
  "create_ddl" text
);

INSERT INTO "rate_limit_blocks" ("create_ddl") VALUES ('CREATE TABLE public.rate_limit_blocks (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  phone_number character varying(20) NOT NULL,
  blocked_at timestamp with time zone NOT NULL,
  unblock_at timestamp with time zone NOT NULL,
  reason character varying(50),
  message_count integer(32,0),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_40059_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_40059_2_not_null" CHECK (phone_number IS NOT NULL),
  CONSTRAINT "2200_40059_3_not_null" CHECK (blocked_at IS NOT NULL),
  CONSTRAINT "2200_40059_4_not_null" CHECK (unblock_at IS NOT NULL),
  CONSTRAINT rate_limit_blocks_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX rate_limit_blocks_pkey ON public.rate_limit_blocks USING btree (id)
  CREATE INDEX idx_rate_limit_blocks_phone ON public.rate_limit_blocks USING btree (phone_number)
  CREATE INDEX idx_rate_limit_blocks_unblock ON public.rate_limit_blocks USING btree (unblock_at)');
