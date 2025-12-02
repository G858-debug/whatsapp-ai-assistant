-- SQL for table: dashboard_analytics

CREATE TABLE IF NOT EXISTS "dashboard_analytics" (
  "create_ddl" text
);

INSERT INTO "dashboard_analytics" ("create_ddl") VALUES ('CREATE TABLE public.dashboard_analytics (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  trainer_id uuid,
  session_id character varying(50),
  event_type character varying(50),
  event_name character varying(100),
  event_data jsonb,
  page_section character varying(50),
  time_on_page integer(32,0),
  device_type character varying(20),
  browser character varying(50),
  os character varying(50),
  screen_size character varying(20),
  is_pwa boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  load_time_ms integer(32,0),
  api_response_time_ms integer(32,0),
  CONSTRAINT "2200_48481_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT dashboard_analytics_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX dashboard_analytics_pkey ON public.dashboard_analytics USING btree (id)
  CREATE INDEX idx_analytics_trainer_date ON public.dashboard_analytics USING btree (trainer_id, created_at DESC)
  CREATE INDEX idx_analytics_event ON public.dashboard_analytics USING btree (event_type, event_name)');
