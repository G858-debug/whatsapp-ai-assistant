create table public.payments (
  id uuid not null default gen_random_uuid (),
  trainer_id uuid null,
  client_id uuid null,
  booking_id uuid null,
  amount numeric(8, 2) not null,
  payment_method character varying(50) null,
  status character varying(20) null default 'pending'::character varying,
  due_date date null,
  paid_date date null,
  notes text null,
  created_at timestamp with time zone null default now(),
  payment_request_id uuid null,
  payment_reference character varying(255) null,
  payment_processor character varying(50) null default 'manual'::character varying,
  processor_fee numeric(8, 2) null default 0,
  platform_fee numeric(8, 2) null default 5.00,
  net_amount numeric(8, 2) null,
  payfast_payment_id character varying(255) null,
  payfast_pf_payment_id character varying(255) null,
  payfast_payment_status character varying(50) null,
  payfast_signature character varying(255) null,
  webhook_data jsonb null,
  payment_token_id uuid null,
  auto_payment boolean null default false,
  payment_type character varying(50) null,
  payment_date timestamp with time zone null,
  constraint payments_pkey primary key (id),
  constraint payments_payment_reference_key unique (payment_reference),
  constraint payments_payment_request_id_fkey foreign KEY (payment_request_id) references payment_requests (id),
  constraint payments_payment_token_id_fkey foreign KEY (payment_token_id) references client_payment_tokens (id)
) TABLESPACE pg_default;

create index IF not exists idx_payments_request_id on public.payments using btree (payment_request_id) TABLESPACE pg_default;

create index IF not exists idx_payments_payment_date on public.payments using btree (payment_date) TABLESPACE pg_default;

create trigger update_token_usage_trigger
after
update on payments for EACH row when (
  new.status::text = 'paid'::text
  and old.status::text <> 'paid'::text
)
execute FUNCTION update_token_usage ();