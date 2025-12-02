-- SQL for table: flow_responses

CREATE TABLE IF NOT EXISTS "flow_responses" (
  "create_ddl" text
);

INSERT INTO "flow_responses" ("create_ddl") VALUES ('CREATE TABLE public.flow_responses (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  flow_token character varying(255) NOT NULL,
  phone_number character varying(20) NOT NULL,
  flow_type character varying(50) NOT NULL,
  response_data jsonb NOT NULL DEFAULT ''{}''::jsonb,
  screen_id character varying(100),
  completed boolean DEFAULT false,
  processed boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_87014_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_87014_2_not_null" CHECK (flow_token IS NOT NULL),
  CONSTRAINT "2200_87014_3_not_null" CHECK (phone_number IS NOT NULL),
  CONSTRAINT "2200_87014_4_not_null" CHECK (flow_type IS NOT NULL),
  CONSTRAINT "2200_87014_5_not_null" CHECK (response_data IS NOT NULL),
  CONSTRAINT flow_responses_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX flow_responses_pkey ON public.flow_responses USING btree (id)
  CREATE INDEX idx_flow_responses_token ON public.flow_responses USING btree (flow_token)
  CREATE INDEX idx_flow_responses_phone ON public.flow_responses USING btree (phone_number)');
