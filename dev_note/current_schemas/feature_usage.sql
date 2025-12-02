-- SQL for table: feature_usage

CREATE TABLE IF NOT EXISTS "feature_usage" (
  "create_ddl" text
);

INSERT INTO "feature_usage" ("create_ddl") VALUES ('CREATE TABLE public.feature_usage (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  trainer_id uuid,
  feature_name character varying(50),
  usage_count integer(32,0) DEFAULT 1,
  last_used timestamp with time zone DEFAULT now(),
  total_time_seconds integer(32,0) DEFAULT 0,
  peak_hour integer(32,0),
  most_used_day character varying(10),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_48496_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT feature_usage_pkey PRIMARY KEY (id),
  CONSTRAINT feature_usage_trainer_id_feature_name_key UNIQUE (trainer_id, feature_name)
);
  CREATE UNIQUE INDEX feature_usage_pkey ON public.feature_usage USING btree (id)
  CREATE UNIQUE INDEX feature_usage_trainer_id_feature_name_key ON public.feature_usage USING btree (trainer_id, feature_name)
  CREATE INDEX idx_feature_usage_trainer ON public.feature_usage USING btree (trainer_id, feature_name)');
