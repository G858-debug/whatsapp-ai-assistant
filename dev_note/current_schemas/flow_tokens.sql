-- SQL for table: flow_tokens

CREATE TABLE IF NOT EXISTS "flow_tokens" (
  "create_ddl" text
);

INSERT INTO "flow_tokens" ("create_ddl") VALUES ('CREATE TABLE public.flow_tokens (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  phone_number character varying(20) NOT NULL,
  flow_token character varying(255) NOT NULL,
  flow_type character varying(50) NOT NULL,
  flow_data jsonb DEFAULT ''{}''::jsonb,
  status character varying(20) DEFAULT ''active''::character varying,
  completed_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_86998_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_86998_2_not_null" CHECK (phone_number IS NOT NULL),
  CONSTRAINT "2200_86998_3_not_null" CHECK (flow_token IS NOT NULL),
  CONSTRAINT "2200_86998_4_not_null" CHECK (flow_type IS NOT NULL),
  CONSTRAINT flow_tokens_flow_token_key UNIQUE (flow_token),
  CONSTRAINT flow_tokens_flow_type_check CHECK (((flow_type)::text = ANY ((ARRAY[''trainer_onboarding''::character varying, ''client_onboarding''::character varying, ''assessment_flow''::character varying, ''booking_flow''::character varying])::text[]))),
  CONSTRAINT flow_tokens_pkey PRIMARY KEY (id),
  CONSTRAINT flow_tokens_status_check CHECK (((status)::text = ANY ((ARRAY[''active''::character varying, ''completed''::character varying, ''expired''::character varying, ''cancelled''::character varying])::text[])))
);
  CREATE UNIQUE INDEX flow_tokens_pkey ON public.flow_tokens USING btree (id)
  CREATE UNIQUE INDEX flow_tokens_flow_token_key ON public.flow_tokens USING btree (flow_token)
  CREATE INDEX idx_flow_tokens_phone ON public.flow_tokens USING btree (phone_number)
  CREATE INDEX idx_flow_tokens_token ON public.flow_tokens USING btree (flow_token)
  CREATE INDEX idx_flow_tokens_type ON public.flow_tokens USING btree (flow_type)');
