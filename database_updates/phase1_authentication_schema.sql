-- ============================================
-- PHASE 1: AUTHENTICATION & ACCOUNT MANAGEMENT
-- Database Schema Updates
-- ============================================

-- 1. CREATE USERS TABLE (Central authentication table)
-- ============================================
CREATE TABLE IF NOT EXISTS public.users (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  phone_number VARCHAR(20) NOT NULL UNIQUE,
  trainer_id VARCHAR(10) NULL,
  client_id VARCHAR(10) NULL,
  login_status VARCHAR(20) NULL DEFAULT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT users_pkey PRIMARY KEY (id),
  CONSTRAINT users_phone_number_key UNIQUE (phone_number),
  CONSTRAINT users_login_status_check CHECK (
    login_status IS NULL OR 
    login_status IN ('trainer', 'client')
  )
);

CREATE INDEX IF NOT EXISTS idx_users_phone_number ON public.users USING btree (phone_number);
CREATE INDEX IF NOT EXISTS idx_users_trainer_id ON public.users USING btree (trainer_id);
CREATE INDEX IF NOT EXISTS idx_users_client_id ON public.users USING btree (client_id);
CREATE INDEX IF NOT EXISTS idx_users_login_status ON public.users USING btree (login_status);


-- 2. ADD UNIQUE ID COLUMNS TO TRAINERS TABLE
-- ============================================
ALTER TABLE public.trainers 
ADD COLUMN IF NOT EXISTS trainer_id VARCHAR(10) UNIQUE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_trainers_trainer_id ON public.trainers (trainer_id);


-- 3. ADD UNIQUE ID COLUMN TO CLIENTS TABLE & REMOVE TRAINER_ID FK
-- ============================================
ALTER TABLE public.clients 
ADD COLUMN IF NOT EXISTS client_id VARCHAR(10) UNIQUE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_client_id ON public.clients (client_id);

-- Drop the old foreign key constraint and trainer_id column
-- (We'll use relationship tables instead)
ALTER TABLE public.clients 
DROP CONSTRAINT IF EXISTS clients_trainer_id_fkey;

ALTER TABLE public.clients 
DROP CONSTRAINT IF EXISTS unique_client_per_trainer;

-- Make trainer_id nullable for now (we'll migrate data to relationship tables)
ALTER TABLE public.clients 
ALTER COLUMN trainer_id DROP NOT NULL;


-- 4. CREATE TRAINER-CLIENT RELATIONSHIP TABLES
-- ============================================

-- Trainer's list of clients
CREATE TABLE IF NOT EXISTS public.trainer_client_list (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  trainer_id VARCHAR(10) NOT NULL,
  client_id VARCHAR(10) NOT NULL,
  connection_status VARCHAR(20) DEFAULT 'active',
  invited_by VARCHAR(20) DEFAULT 'trainer',
  invitation_token VARCHAR(255) NULL,
  invited_at TIMESTAMP WITH TIME ZONE NULL,
  approved_at TIMESTAMP WITH TIME ZONE NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT trainer_client_list_pkey PRIMARY KEY (id),
  CONSTRAINT trainer_client_list_unique UNIQUE (trainer_id, client_id),
  CONSTRAINT trainer_client_list_status_check CHECK (
    connection_status IN ('pending', 'active', 'declined', 'removed')
  ),
  CONSTRAINT trainer_client_list_invited_by_check CHECK (
    invited_by IN ('trainer', 'client')
  )
);

CREATE INDEX IF NOT EXISTS idx_trainer_client_list_trainer ON public.trainer_client_list (trainer_id);
CREATE INDEX IF NOT EXISTS idx_trainer_client_list_client ON public.trainer_client_list (client_id);
CREATE INDEX IF NOT EXISTS idx_trainer_client_list_status ON public.trainer_client_list (connection_status);
CREATE INDEX IF NOT EXISTS idx_trainer_client_list_token ON public.trainer_client_list (invitation_token);


-- Client's list of trainers (subscribed trainers)
CREATE TABLE IF NOT EXISTS public.client_trainer_list (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  client_id VARCHAR(10) NOT NULL,
  trainer_id VARCHAR(10) NOT NULL,
  connection_status VARCHAR(20) DEFAULT 'active',
  invited_by VARCHAR(20) DEFAULT 'client',
  invitation_token VARCHAR(255) NULL,
  invited_at TIMESTAMP WITH TIME ZONE NULL,
  approved_at TIMESTAMP WITH TIME ZONE NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT client_trainer_list_pkey PRIMARY KEY (id),
  CONSTRAINT client_trainer_list_unique UNIQUE (client_id, trainer_id),
  CONSTRAINT client_trainer_list_status_check CHECK (
    connection_status IN ('pending', 'active', 'declined', 'removed')
  ),
  CONSTRAINT client_trainer_list_invited_by_check CHECK (
    invited_by IN ('trainer', 'client')
  )
);

CREATE INDEX IF NOT EXISTS idx_client_trainer_list_client ON public.client_trainer_list (client_id);
CREATE INDEX IF NOT EXISTS idx_client_trainer_list_trainer ON public.client_trainer_list (trainer_id);
CREATE INDEX IF NOT EXISTS idx_client_trainer_list_status ON public.client_trainer_list (connection_status);
CREATE INDEX IF NOT EXISTS idx_client_trainer_list_token ON public.client_trainer_list (invitation_token);


-- 5. CREATE TASK TRACKING TABLES
-- ============================================

-- Trainer tasks
CREATE TABLE IF NOT EXISTS public.trainer_tasks (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  trainer_id VARCHAR(10) NOT NULL,
  task_type VARCHAR(50) NOT NULL,
  task_status VARCHAR(20) DEFAULT 'running',
  task_data JSONB DEFAULT '{}',
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE NULL,
  stopped_at TIMESTAMP WITH TIME ZONE NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT trainer_tasks_pkey PRIMARY KEY (id),
  CONSTRAINT trainer_tasks_status_check CHECK (
    task_status IN ('running', 'completed', 'stopped', 'failed')
  )
);

CREATE INDEX IF NOT EXISTS idx_trainer_tasks_trainer_id ON public.trainer_tasks (trainer_id);
CREATE INDEX IF NOT EXISTS idx_trainer_tasks_status ON public.trainer_tasks (task_status);
CREATE INDEX IF NOT EXISTS idx_trainer_tasks_type ON public.trainer_tasks (task_type);
CREATE INDEX IF NOT EXISTS idx_trainer_tasks_started ON public.trainer_tasks (started_at DESC);


-- Client tasks
CREATE TABLE IF NOT EXISTS public.client_tasks (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  client_id VARCHAR(10) NOT NULL,
  task_type VARCHAR(50) NOT NULL,
  task_status VARCHAR(20) DEFAULT 'running',
  task_data JSONB DEFAULT '{}',
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE NULL,
  stopped_at TIMESTAMP WITH TIME ZONE NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT client_tasks_pkey PRIMARY KEY (id),
  CONSTRAINT client_tasks_status_check CHECK (
    task_status IN ('running', 'completed', 'stopped', 'failed')
  )
);

CREATE INDEX IF NOT EXISTS idx_client_tasks_client_id ON public.client_tasks (client_id);
CREATE INDEX IF NOT EXISTS idx_client_tasks_status ON public.client_tasks (task_status);
CREATE INDEX IF NOT EXISTS idx_client_tasks_type ON public.client_tasks (task_type);
CREATE INDEX IF NOT EXISTS idx_client_tasks_started ON public.client_tasks (started_at DESC);


-- 6. UPDATE CONVERSATION_STATES TABLE
-- ============================================
ALTER TABLE public.conversation_states 
ADD COLUMN IF NOT EXISTS login_status VARCHAR(20) NULL DEFAULT NULL;

ALTER TABLE public.conversation_states 
ADD COLUMN IF NOT EXISTS current_task_id UUID NULL;

CREATE INDEX IF NOT EXISTS idx_conversation_states_login_status ON public.conversation_states (login_status);


-- 7. CLEANUP OLD CLIENT RECORDS (OPTIONAL - RUN MANUALLY IF NEEDED)
-- ============================================
-- Uncomment below to delete all existing client records
-- WARNING: This will delete all client data!
-- DELETE FROM public.clients;


-- ============================================
-- MIGRATION NOTES:
-- ============================================
-- After running this SQL:
-- 1. Existing trainer records will have NULL trainer_id (will be generated on first login)
-- 2. Existing client records will have NULL client_id (will be generated on first login)
-- 3. Old client-trainer relationships in clients.trainer_id will need manual migration if you want to preserve them
-- 4. New registrations will automatically get unique IDs generated
-- ============================================
