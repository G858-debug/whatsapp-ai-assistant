-- SQL for table: assessment_photos

CREATE TABLE IF NOT EXISTS "assessment_photos" (
  "create_ddl" text
);

INSERT INTO "assessment_photos" ("create_ddl") VALUES ('CREATE TABLE public.assessment_photos (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  assessment_id uuid,
  client_id uuid,
  photo_type character varying(50),
  photo_url text NOT NULL,
  thumbnail_url text,
  caption text,
  uploaded_at timestamp with time zone DEFAULT now(),
  is_deleted boolean DEFAULT false,
  CONSTRAINT "2200_28991_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_28991_5_not_null" CHECK (photo_url IS NOT NULL),
  CONSTRAINT assessment_photos_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES public.fitness_assessments(id),
  CONSTRAINT assessment_photos_pkey PRIMARY KEY (id)
);
  CREATE UNIQUE INDEX assessment_photos_pkey ON public.assessment_photos USING btree (id)
  CREATE INDEX idx_photos_assessment ON public.assessment_photos USING btree (assessment_id)
  CREATE INDEX idx_photos_client ON public.assessment_photos USING btree (client_id)');
