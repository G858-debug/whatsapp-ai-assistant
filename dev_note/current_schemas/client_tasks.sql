create table public.client_tasks (
  id uuid not null default gen_random_uuid (),
  client_id character varying(20) not null,
  task_type character varying(50) not null,
  task_status character varying(20) null default 'running'::character varying,
  task_data jsonb null default '{}'::jsonb,
  started_at timestamp with time zone null default now(),
  completed_at timestamp with time zone null,
  stopped_at timestamp with time zone null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint client_tasks_pkey primary key (id),
  constraint client_tasks_status_check check (
    (
      (task_status)::text = any (
        (
          array[
            'running'::character varying,
            'completed'::character varying,
            'stopped'::character varying,
            'failed'::character varying
          ]
        )::text[]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_client_tasks_status on public.client_tasks using btree (task_status) TABLESPACE pg_default;

create index IF not exists idx_client_tasks_type on public.client_tasks using btree (task_type) TABLESPACE pg_default;

create index IF not exists idx_client_tasks_started on public.client_tasks using btree (started_at desc) TABLESPACE pg_default;

create index IF not exists idx_client_tasks_client_id on public.client_tasks using btree (client_id) TABLESPACE pg_default;