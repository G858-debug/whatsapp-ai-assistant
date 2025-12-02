create table public.trainer_subscriptions (
  id uuid not null default gen_random_uuid (),
  trainer_id uuid null,
  plan_id uuid null,
  status character varying(50) null default 'active'::character varying,
  billing_cycle character varying(20) null default 'monthly'::character varying,
  current_period_start timestamp with time zone null,
  current_period_end timestamp with time zone null,
  payfast_token character varying(255) null,
  payfast_subscription_id character varying(255) null,
  payfast_profile_id character varying(255) null,
  cancelled_at timestamp with time zone null,
  cancellation_reason text null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  plan character varying(50) null,
  price numeric(10, 2) null,
  auto_renew boolean null default true,
  ended_at timestamp with time zone null,
  constraint trainer_subscriptions_pkey primary key (id),
  constraint trainer_subscriptions_trainer_id_key unique (trainer_id),
  constraint trainer_subscriptions_plan_id_fkey foreign KEY (plan_id) references subscription_plans (id)
) TABLESPACE pg_default;

create index IF not exists idx_trainer_subscriptions_trainer on public.trainer_subscriptions using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_trainer_subscriptions_status on public.trainer_subscriptions using btree (status) TABLESPACE pg_default;

create index IF not exists idx_trainer_subscriptions_plan on public.trainer_subscriptions using btree (plan) TABLESPACE pg_default;

create index IF not exists idx_trainer_subscriptions_billing_cycle on public.trainer_subscriptions using btree (billing_cycle) TABLESPACE pg_default;

create trigger update_trainer_subscription_trigger
after INSERT
or
update on trainer_subscriptions for EACH row
execute FUNCTION update_trainer_subscription_status ();