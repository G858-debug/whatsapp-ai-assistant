-- Create registration states table for managing registration flow
CREATE TABLE IF NOT EXISTS registration_states (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    current_step INTEGER DEFAULT 0,
    data JSONB DEFAULT '{}',
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX idx_registration_states_phone ON registration_states(phone_number);
CREATE INDEX idx_registration_states_completed ON registration_states(completed);

-- Add RLS policies
ALTER TABLE registration_states ENABLE ROW LEVEL SECURITY;

-- Rollback:
-- DROP TABLE IF EXISTS registration_states;