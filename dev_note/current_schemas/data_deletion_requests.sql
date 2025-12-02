-- SQL for table: data_deletion_requests

CREATE TABLE IF NOT EXISTS "data_deletion_requests" (
  "create_ddl" text
);

INSERT INTO "data_deletion_requests" ("create_ddl") VALUES ('CREATE TABLE public.data_deletion_requests (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  user_type character varying(20),
  full_name character varying(255),
  email character varying(255),
  phone character varying(20),
  reason text,
  status character varying(20) DEFAULT ''pending''::character varying,
  requested_at timestamp without time zone DEFAULT now(),
  process_by timestamp without time zone,
  completed_at timestamp without time zone,
  ip_address character varying(45),
  error text,
  CONSTRAINT "2200_38923_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT data_deletion_requests_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX data_deletion_requests_pkey ON public.data_deletion_requests USING btree (id)
  CREATE INDEX idx_deletion_status ON public.data_deletion_requests USING btree (status, process_by)');
