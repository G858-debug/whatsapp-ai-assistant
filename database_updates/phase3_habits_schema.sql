-- ============================================
-- PHASE 3: FITNESS HABIT MANAGEMENT
-- Database Schema Updates
-- ============================================

-- 1. CREATE FITNESS_HABITS TABLE
-- ============================================
-- Stores habits created by trainers
CREATE TABLE IF NOT EXISTS public.fitness_habits (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  habit_id VARCHAR(10) NOT NULL UNIQUE,
  trainer_id VARCHAR(10) NOT NULL,
  habit_name VARCHAR(100) NOT NULL,
  description TEXT NULL,
  target_value DECIMAL(10,2) NOT NULL,
  unit VARCHAR(50) NOT NULL,
  frequency VARCHAR(20) NOT NULL DEFAULT 'daily',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT fitness_habits_pkey PRIMARY KEY (id),
  CONSTRAINT fitness_habits_habit_id_key UNIQUE (habit_id),
  CONSTRAINT fitness_habits_frequency_check CHECK (
    frequency IN ('daily', 'weekly')
  )
);

CREATE INDEX IF NOT EXISTS idx_fitness_habits_trainer ON public.fitness_habits (trainer_id);
CREATE INDEX IF NOT EXISTS idx_fitness_habits_habit_id ON public.fitness_habits (habit_id);
CREATE INDEX IF NOT EXISTS idx_fitness_habits_active ON public.fitness_habits (is_active);
CREATE INDEX IF NOT EXISTS idx_fitness_habits_trainer_active ON public.fitness_habits (trainer_id, is_active);


-- 2. CREATE TRAINEE_HABIT_ASSIGNMENTS TABLE
-- ============================================
-- Links habits to clients (many-to-many relationship)
CREATE TABLE IF NOT EXISTS public.trainee_habit_assignments (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  habit_id VARCHAR(10) NOT NULL,
  client_id VARCHAR(10) NOT NULL,
  trainer_id VARCHAR(10) NOT NULL,
  assigned_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT trainee_habit_assignments_pkey PRIMARY KEY (id),
  CONSTRAINT trainee_habit_assignments_unique UNIQUE (habit_id, client_id),
  CONSTRAINT trainee_habit_assignments_habit_fkey FOREIGN KEY (habit_id) 
    REFERENCES public.fitness_habits(habit_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_habit_assignments_client ON public.trainee_habit_assignments (client_id);
CREATE INDEX IF NOT EXISTS idx_habit_assignments_habit ON public.trainee_habit_assignments (habit_id);
CREATE INDEX IF NOT EXISTS idx_habit_assignments_trainer ON public.trainee_habit_assignments (trainer_id);
CREATE INDEX IF NOT EXISTS idx_habit_assignments_active ON public.trainee_habit_assignments (is_active);
CREATE INDEX IF NOT EXISTS idx_habit_assignments_client_active ON public.trainee_habit_assignments (client_id, is_active);


-- 3. CREATE HABIT_LOGS TABLE
-- ============================================
-- Stores habit log entries (IMMUTABLE - no edits/deletes allowed)
-- Multiple logs per day are allowed
CREATE TABLE IF NOT EXISTS public.habit_logs (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  habit_id VARCHAR(10) NOT NULL,
  client_id VARCHAR(10) NOT NULL,
  log_date DATE NOT NULL,
  log_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_value DECIMAL(10,2) NOT NULL,
  notes TEXT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT habit_logs_pkey PRIMARY KEY (id),
  CONSTRAINT habit_logs_habit_fkey FOREIGN KEY (habit_id) 
    REFERENCES public.fitness_habits(habit_id) ON DELETE CASCADE,
  CONSTRAINT habit_logs_completed_value_check CHECK (completed_value >= 0)
);

CREATE INDEX IF NOT EXISTS idx_habit_logs_client ON public.habit_logs (client_id);
CREATE INDEX IF NOT EXISTS idx_habit_logs_habit ON public.habit_logs (habit_id);
CREATE INDEX IF NOT EXISTS idx_habit_logs_date ON public.habit_logs (log_date);
CREATE INDEX IF NOT EXISTS idx_habit_logs_client_date ON public.habit_logs (client_id, log_date);
CREATE INDEX IF NOT EXISTS idx_habit_logs_habit_date ON public.habit_logs (habit_id, log_date);
CREATE INDEX IF NOT EXISTS idx_habit_logs_client_habit_date ON public.habit_logs (client_id, habit_id, log_date);
CREATE INDEX IF NOT EXISTS idx_habit_logs_time ON public.habit_logs (log_time DESC);


-- 4. CREATE TRIGGER FOR UPDATED_AT COLUMNS
-- ============================================
-- Update updated_at timestamp on record update
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to fitness_habits
DROP TRIGGER IF EXISTS update_fitness_habits_updated_at ON public.fitness_habits;
CREATE TRIGGER update_fitness_habits_updated_at
  BEFORE UPDATE ON public.fitness_habits
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to trainee_habit_assignments
DROP TRIGGER IF EXISTS update_trainee_habit_assignments_updated_at ON public.trainee_habit_assignments;
CREATE TRIGGER update_trainee_habit_assignments_updated_at
  BEFORE UPDATE ON public.trainee_habit_assignments
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- NOTES:
-- ============================================
-- 1. habit_logs table is IMMUTABLE by design:
--    - No UPDATE or DELETE operations should be performed
--    - Application layer should prevent edits/deletes
--    - Multiple logs per day are allowed (each with unique timestamp)
--
-- 2. Progress calculation:
--    - Sum all completed_value entries for a habit on a given date
--    - Compare sum against target_value from fitness_habits table
--
-- 3. Soft deletes:
--    - fitness_habits uses is_active flag for soft deletes
--    - trainee_habit_assignments uses is_active flag for unassignments
--
-- 4. Foreign keys:
--    - habit_id references fitness_habits(habit_id) with CASCADE delete
--    - When a habit is deleted, all assignments and logs are also deleted
--
-- 5. ID Generation:
--    - habit_id: 5-7 character VARCHAR (e.g., HAB123, HABWAT45)
--    - Generated in application layer using habit name + numbers
--    - Must be unique across all habits
-- ============================================
