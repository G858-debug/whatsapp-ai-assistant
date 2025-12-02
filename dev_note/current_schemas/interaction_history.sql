-- SQL for table: interaction_history

CREATE TABLE IF NOT EXISTS "interaction_history" (
  "create_ddl" text
);

INSERT INTO "interaction_history" ("create_ddl") VALUES ('CREATE TABLE public.interaction_history (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  phone_number character varying(20) NOT NULL,
  first_interaction_at timestamp with time zone DEFAULT now(),
  last_interaction_at timestamp with time zone DEFAULT now(),
  interaction_count integer(32,0) DEFAULT 1,
  user_type character varying(20),
  CONSTRAINT "2200_18543_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_18543_2_not_null" CHECK (phone_number IS NOT NULL),
  CONSTRAINT interaction_history_phone_number_key UNIQUE (phone_number),
  CONSTRAINT interaction_history_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX interaction_history_pkey ON public.interaction_history USING btree (id)
  CREATE UNIQUE INDEX interaction_history_phone_number_key ON public.interaction_history USING btree (phone_number)
  CREATE INDEX idx_interaction_history_phone ON public.interaction_history USING btree (phone_number)');
