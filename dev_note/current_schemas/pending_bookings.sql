-- SQL for table: pending_bookings

CREATE TABLE IF NOT EXISTS "pending_bookings" (
  "create_ddl" text
);

INSERT INTO "pending_bookings" ("create_ddl") VALUES ('CREATE TABLE public.pending_bookings (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  trainer_id uuid,
  client_id uuid,
  proposed_datetime timestamp with time zone NOT NULL,
  proposed_duration integer(32,0) DEFAULT 60,
  expires_at timestamp with time zone NOT NULL,
  status character varying(20) DEFAULT ''pending''::character varying,
  created_at timestamp with time zone DEFAULT now(),
  confirmed_at timestamp with time zone,
  booking_id uuid,
  CONSTRAINT "2200_18517_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_18517_4_not_null" CHECK (proposed_datetime IS NOT NULL),
  CONSTRAINT "2200_18517_6_not_null" CHECK (expires_at IS NOT NULL),
  CONSTRAINT pending_bookings_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX pending_bookings_pkey ON public.pending_bookings USING btree (id)
  CREATE INDEX idx_pending_bookings_client ON public.pending_bookings USING btree (client_id, status)
  CREATE INDEX idx_pending_bookings_expires ON public.pending_bookings USING btree (expires_at) WHERE ((status)::text = ''pending''::text)');
