create table public.dashboard_notifications (
  id uuid not null default gen_random_uuid (),
  trainer_id uuid null,
  client_id uuid null,
  notification_type character varying(50) null,
  message text null,
  is_read boolean null default false,
  created_at timestamp with time zone null default now(),
  constraint dashboard_notifications_pkey primary key (id),
  constraint dashboard_notifications_client_id_fkey foreign KEY (client_id) references clients (id) on delete CASCADE,
  constraint dashboard_notifications_trainer_id_fkey foreign KEY (trainer_id) references trainers (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_dashboard_notifications_trainer on public.dashboard_notifications using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_dashboard_notifications_read on public.dashboard_notifications using btree (is_read) TABLESPACE pg_default;