-- SQL for table: subscription_plans

CREATE TABLE IF NOT EXISTS "subscription_plans" (
  "create_ddl" text
);

INSERT INTO "subscription_plans" ("create_ddl") VALUES ('CREATE TABLE public.subscription_plans (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  plan_name character varying(100) NOT NULL,
  plan_code character varying(50) NOT NULL,
  price_monthly numeric(8,2) NOT NULL,
  price_annual numeric(8,2),
  max_clients integer(32,0) NOT NULL,
  payfast_product_id character varying(100),
  is_active boolean DEFAULT true,
  display_order integer(32,0) DEFAULT 0,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT "2200_36912_1_not_null" CHECK (id IS NOT NULL),
  CONSTRAINT "2200_36912_2_not_null" CHECK (plan_name IS NOT NULL),
  CONSTRAINT "2200_36912_3_not_null" CHECK (plan_code IS NOT NULL),
  CONSTRAINT "2200_36912_4_not_null" CHECK (price_monthly IS NOT NULL),
  CONSTRAINT "2200_36912_6_not_null" CHECK (max_clients IS NOT NULL),
  CONSTRAINT subscription_plans_pkey PRIMARY KEY (id),
  CONSTRAINT subscription_plans_plan_code_key UNIQUE (plan_code)
);
  CREATE UNIQUE INDEX subscription_plans_pkey ON public.subscription_plans USING btree (id)
  CREATE UNIQUE INDEX subscription_plans_plan_code_key ON public.subscription_plans USING btree (plan_code)');
