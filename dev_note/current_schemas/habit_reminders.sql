create table public.habit_reminders (
  id uuid not null default gen_random_uuid (),
  client_id character varying(10) not null,
  reminder_date date not null,
  reminder_time time without time zone not null,
  sent_at timestamp with time zone null,
  total_habits integer not null default 0,
  completed_habits integer not null default 0,
  remaining_habits integer not null default 0,
  reminder_type character varying(20) null default 'daily'::character varying,
  status character varying(20) null default 'pending'::character varying,
  message_sent text null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint habit_reminders_pkey primary key (id),
  constraint habit_reminders_client_date_unique unique (client_id, reminder_date),
  constraint habit_reminders_status_check check (
    (
      (status)::text = any (
        (
          array[
            'pending'::character varying,
            'sent'::character varying,
            'failed'::character varying
          ]
        )::text[]
      )
    )
  ),
  constraint habit_reminders_type_check check (
    (
      (reminder_type)::text = any (
        (
          array[
            'daily'::character varying,
            'weekly'::character varying,
            'custom'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_habit_reminders_client on public.habit_reminders using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_habit_reminders_date on public.habit_reminders using btree (reminder_date) TABLESPACE pg_default;

create index IF not exists idx_habit_reminders_status on public.habit_reminders using btree (status) TABLESPACE pg_default;

create index IF not exists idx_habit_reminders_sent_at on public.habit_reminders using btree (sent_at) TABLESPACE pg_default;

create index IF not exists idx_habit_reminders_client_date on public.habit_reminders using btree (client_id, reminder_date) TABLESPACE pg_default;