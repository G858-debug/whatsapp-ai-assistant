-- Additional Migration: Add Workouts Table
-- Run this after the main migration to add the missing workouts table

-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS workouts CASCADE;

CREATE TABLE workouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    workout_type VARCHAR(50) DEFAULT 'general' CHECK (workout_type IN ('strength', 'cardio', 'flexibility', 'general')),
    duration_minutes INTEGER DEFAULT 60,
    difficulty_level VARCHAR(20) DEFAULT 'medium' CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    exercises JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workouts indexes
CREATE INDEX IF NOT EXISTS idx_workouts_trainer ON workouts(trainer_id);
CREATE INDEX IF NOT EXISTS idx_workouts_client ON workouts(client_id);
CREATE INDEX IF NOT EXISTS idx_workouts_type ON workouts(workout_type);
CREATE INDEX IF NOT EXISTS idx_workouts_difficulty ON workouts(difficulty_level);

-- Enable RLS on workouts table
ALTER TABLE workouts ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Trainers can manage their workouts" ON workouts;
DROP POLICY IF EXISTS "Clients can view their workouts" ON workouts;

-- Workout policies
CREATE POLICY "Trainers can manage their workouts" ON workouts
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Clients can view their workouts" ON workouts
    FOR SELECT USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

COMMENT ON TABLE workouts IS 'Workout plans and exercises for clients';
