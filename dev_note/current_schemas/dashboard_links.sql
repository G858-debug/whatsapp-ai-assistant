-- SQL for table: dashboard_links

CREATE TABLE IF NOT EXISTS "dashboard_links" (
  "create_ddl" text
);

INSERT INTO "dashboard_links" ("create_ddl") VALUES ('CREATE TABLE public.dashboard_links (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  trainer_id uuid,
  short_code character varying(10) NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  last_accessed timestamp with time zone DEFAULT now(),
  expires_at timestamp with time zone,
  access_count integer(32,0) DEFAULT 0,
  is_active boolean DEFAULT true,
  cached_data jsonb,
  cache_updated_at timestamp with time zone,
  CONSTRAINT "2200_45124_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_45124_3_not_null" CHECK (short_code IS NOT NULL),
  CONSTRAINT dashboard_links_pkey PRIMARY KEY (id),
  CONSTRAINT dashboard_links_short_code_key UNIQUE (short_code),
  CONSTRAINT dashboard_links_trainer_id_key UNIQUE (trainer_id)
);
  CREATE UNIQUE INDEX dashboard_links_pkey ON public.dashboard_links USING btree (id)
  CREATE UNIQUE INDEX dashboard_links_trainer_id_key ON public.dashboard_links USING btree (trainer_id)
  CREATE UNIQUE INDEX dashboard_links_short_code_key ON public.dashboard_links USING btree (short_code)
  CREATE INDEX idx_links_short_code ON public.dashboard_links USING btree (short_code)
  CREATE INDEX idx_links_trainer ON public.dashboard_links USING btree (trainer_id)');
