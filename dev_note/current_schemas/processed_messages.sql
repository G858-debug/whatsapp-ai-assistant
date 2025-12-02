-- SQL for table: processed_messages

CREATE TABLE IF NOT EXISTS "processed_messages" (
  "create_ddl" text
);

INSERT INTO "processed_messages" ("create_ddl") VALUES ('CREATE TABLE public.processed_messages (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  whatsapp_message_id character varying(255) NOT NULL,
  phone_number character varying(20) NOT NULL,
  message_text text,
  "timestamp" character varying(20),
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_70906_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_70906_2_not_null" CHECK (whatsapp_message_id IS NOT NULL),
  CONSTRAINT "2200_70906_3_not_null" CHECK (phone_number IS NOT NULL),
  CONSTRAINT processed_messages_pkey PRIMARY KEY (id),
  CONSTRAINT processed_messages_whatsapp_message_id_key UNIQUE (whatsapp_message_id)
);
  CREATE UNIQUE INDEX processed_messages_pkey ON public.processed_messages USING btree (id)
  CREATE UNIQUE INDEX processed_messages_whatsapp_message_id_key ON public.processed_messages USING btree (whatsapp_message_id)
  CREATE INDEX idx_processed_messages_whatsapp_id ON public.processed_messages USING btree (whatsapp_message_id)
  CREATE INDEX idx_processed_messages_phone ON public.processed_messages USING btree (phone_number)
  CREATE INDEX idx_processed_messages_created ON public.processed_messages USING btree (created_at)');
