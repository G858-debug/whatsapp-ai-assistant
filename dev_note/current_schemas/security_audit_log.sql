-- SQL for table: security_audit_log

CREATE TABLE IF NOT EXISTS "security_audit_log" (
  "create_ddl" text
);

INSERT INTO "security_audit_log" ("create_ddl") VALUES ('CREATE TABLE public.security_audit_log (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  event_type character varying(50),
  phone_number character varying(20),
  ip_address character varying(45),
  details jsonb,
  severity character varying(20) DEFAULT ''medium''::character varying,
  resolved boolean DEFAULT false,
  resolved_by uuid,
  resolved_at timestamp with time zone,
  notes text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_42400_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT security_audit_log_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX security_audit_log_pkey ON public.security_audit_log USING btree (id)
  CREATE INDEX idx_audit_phone ON public.security_audit_log USING btree (phone_number)
  CREATE INDEX idx_audit_event ON public.security_audit_log USING btree (event_type)
  CREATE INDEX idx_audit_created ON public.security_audit_log USING btree (created_at DESC)
  CREATE INDEX idx_audit_severity ON public.security_audit_log USING btree (severity)');
