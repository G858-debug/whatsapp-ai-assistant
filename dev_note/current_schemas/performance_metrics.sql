-- SQL for table: performance_metrics

CREATE TABLE IF NOT EXISTS "performance_metrics" (
  "create_ddl" text
);

INSERT INTO "performance_metrics" ("create_ddl") VALUES ('CREATE TABLE public.performance_metrics (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  trainer_id uuid,
  metric_type character varying(50),
  metric_name character varying(100),
  value_ms integer(32,0),
  "timestamp" timestamp with time zone DEFAULT now(),
  device_type character varying(20),
  network_type character varying(20),
  cache_hit boolean DEFAULT false,
  CONSTRAINT "2200_48535_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT performance_metrics_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX performance_metrics_pkey ON public.performance_metrics USING btree (id)
  CREATE INDEX idx_performance_timestamp ON public.performance_metrics USING btree ("timestamp" DESC)');
