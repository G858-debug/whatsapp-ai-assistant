create table public.fitness_assessments (
  id uuid not null default gen_random_uuid (),
  client_id uuid null,
  trainer_id uuid null,
  template_id uuid null,
  assessment_date timestamp with time zone null default now(),
  assessment_type character varying(50) null default 'initial'::character varying,
  status character varying(20) null default 'pending'::character varying,
  completed_by character varying(20) null,
  access_token character varying(255) null,
  token_expires_at timestamp with time zone null,
  form_opened_at timestamp with time zone null,
  form_completed_at timestamp with time zone null,
  current_medications text[] null,
  supplements text[] null,
  past_injuries jsonb null,
  surgeries jsonb null,
  chronic_conditions text[] null,
  pain_areas text[] null,
  family_health_history text null,
  doctor_clearance boolean null,
  doctor_clearance_notes text null,
  occupation character varying(100) null,
  work_activity_level character varying(20) null,
  sleep_hours_per_night numeric(3, 1) null,
  sleep_quality character varying(20) null,
  stress_level integer null,
  stress_management text null,
  smoking_status character varying(20) null,
  alcohol_frequency character varying(50) null,
  nutrition_notes text null,
  dietary_restrictions text[] null,
  water_intake_liters numeric(3, 1) null,
  current_exercise_routine text null,
  trainer_notes text null,
  client_notes text null,
  red_flags text[] null,
  requires_medical_clearance boolean null default false,
  next_assessment_date timestamp with time zone null,
  reminder_sent boolean null default false,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  responses jsonb null default '{}'::jsonb,
  due_date timestamp with time zone null,
  constraint fitness_assessments_pkey primary key (id),
  constraint fitness_assessments_access_token_key unique (access_token),
  constraint fitness_assessments_template_id_fkey foreign KEY (template_id) references assessment_templates (id),
  constraint fitness_assessments_stress_level_check check (
    (
      (stress_level is null)
      or (
        (stress_level >= 1)
        and (stress_level <= 10)
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_assessments_client on public.fitness_assessments using btree (client_id) TABLESPACE pg_default;

create index IF not exists idx_assessments_trainer on public.fitness_assessments using btree (trainer_id) TABLESPACE pg_default;

create index IF not exists idx_assessments_token on public.fitness_assessments using btree (access_token) TABLESPACE pg_default;

create index IF not exists idx_assessments_status on public.fitness_assessments using btree (status) TABLESPACE pg_default;

create trigger schedule_next_assessment_trigger BEFORE
update on fitness_assessments for EACH row when (
  old.status::text <> 'completed'::text
  and new.status::text = 'completed'::text
)
execute FUNCTION schedule_next_assessment ();