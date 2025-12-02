-- SQL for table: assessment_access_tokens

CREATE TABLE IF NOT EXISTS "assessment_access_tokens" (
  "create_ddl" text
);

INSERT INTO "assessment_access_tokens" ("create_ddl") VALUES ('CREATE TABLE public.assessment_access_tokens (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  token character varying(255) NOT NULL,
  client_id uuid,
  created_at timestamp with time zone DEFAULT now(),
  expires_at timestamp with time zone NOT NULL,
  used_count integer(32,0) DEFAULT 0,
  last_accessed timestamp with time zone,
  CONSTRAINT "2200_33564_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_33564_2_not_null" CHECK (token IS NOT NULL),
  CONSTRAINT "2200_33564_5_not_null" CHECK (expires_at IS NOT NULL),
  CONSTRAINT assessment_access_tokens_pkey PRIMARY KEY (id),
  CONSTRAINT assessment_access_tokens_token_key UNIQUE (token)
);
  CREATE UNIQUE INDEX assessment_access_tokens_pkey ON public.assessment_access_tokens USING btree (id)
  CREATE UNIQUE INDEX assessment_access_tokens_token_key ON public.assessment_access_tokens USING btree (token)
  CREATE INDEX idx_assessment_tokens ON public.assessment_access_tokens USING btree (token)');
