-- SQL for table: engagement_metrics

CREATE TABLE IF NOT EXISTS "engagement_metrics" (
  "create_ddl" text
);

INSERT INTO "engagement_metrics" ("create_ddl") VALUES ('CREATE TABLE public.engagement_metrics (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  trainer_id uuid,
  total_sessions integer(32,0) DEFAULT 0,
  total_page_views integer(32,0) DEFAULT 0,
  avg_session_duration integer(32,0),
  bounce_rate numeric(5,2),
  first_visit date,
  last_visit date,
  days_active integer(32,0) DEFAULT 0,
  consecutive_days integer(32,0) DEFAULT 0,
  preferred_device character varying(20),
  preferred_time character varying(20),
  most_viewed_section character varying(50),
  exports_count integer(32,0) DEFAULT 0,
  installed_pwa boolean DEFAULT false,
  pwa_install_date date,
  opens_from_pwa integer(32,0) DEFAULT 0,
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_48514_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT engagement_metrics_pkey PRIMARY KEY (id),
  CONSTRAINT engagement_metrics_trainer_id_key UNIQUE (trainer_id)
);
  CREATE UNIQUE INDEX engagement_metrics_pkey ON public.engagement_metrics USING btree (id)
  CREATE UNIQUE INDEX engagement_metrics_trainer_id_key ON public.engagement_metrics USING btree (trainer_id)
  CREATE INDEX idx_engagement_trainer ON public.engagement_metrics USING btree (trainer_id)');
