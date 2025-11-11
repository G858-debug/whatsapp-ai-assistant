-- Migration: Add privacy columns to trainer_client_list for multi-trainer support
-- Date: 2025-11-11
-- Purpose: Store trainer-specific data (pricing, notes) separate from shared client profile

-- ============================================================================
-- Add columns to trainer_client_list
-- ============================================================================

-- Add custom_price_per_session column (trainer-specific pricing)
ALTER TABLE trainer_client_list
ADD COLUMN IF NOT EXISTS custom_price_per_session DECIMAL(10, 2) DEFAULT NULL;

-- Add private_notes column (trainer-specific notes)
ALTER TABLE trainer_client_list
ADD COLUMN IF NOT EXISTS private_notes TEXT DEFAULT NULL;

-- Add sessions_count column (track number of sessions)
ALTER TABLE trainer_client_list
ADD COLUMN IF NOT EXISTS sessions_count INTEGER DEFAULT 0;

-- Add updated_at column if it doesn't exist
ALTER TABLE trainer_client_list
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add comments for documentation
COMMENT ON COLUMN trainer_client_list.custom_price_per_session IS 'Trainer-specific custom pricing per session (privacy: only this trainer sees this)';
COMMENT ON COLUMN trainer_client_list.private_notes IS 'Trainer-specific private notes about client (privacy: only this trainer sees this)';
COMMENT ON COLUMN trainer_client_list.sessions_count IS 'Count of sessions between this trainer and client';
COMMENT ON COLUMN trainer_client_list.updated_at IS 'Last update timestamp for this relationship';

-- ============================================================================
-- Create indexes for performance
-- ============================================================================

-- Index for filtering by pricing
CREATE INDEX IF NOT EXISTS idx_trainer_client_list_pricing
ON trainer_client_list(trainer_id, client_id, custom_price_per_session);

-- Index for updated_at queries
CREATE INDEX IF NOT EXISTS idx_trainer_client_list_updated_at
ON trainer_client_list(updated_at DESC);

-- ============================================================================
-- Create trigger to auto-update updated_at timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION update_trainer_client_list_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_trainer_client_list_updated_at ON trainer_client_list;

CREATE TRIGGER trigger_update_trainer_client_list_updated_at
BEFORE UPDATE ON trainer_client_list
FOR EACH ROW
EXECUTE FUNCTION update_trainer_client_list_updated_at();

-- ============================================================================
-- Row Level Security (RLS) Policies
-- ============================================================================

-- Enable RLS on trainer_client_list if not already enabled
ALTER TABLE trainer_client_list ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "trainers_see_own_relationships" ON trainer_client_list;
DROP POLICY IF EXISTS "clients_see_own_relationships" ON trainer_client_list;
DROP POLICY IF EXISTS "trainers_update_own_relationships" ON trainer_client_list;

-- Policy 1: Trainers can only see their own relationships
CREATE POLICY "trainers_see_own_relationships" ON trainer_client_list
FOR SELECT
USING (
    auth.uid()::text = trainer_id
    OR
    -- Allow service role full access
    auth.jwt() ->> 'role' = 'service_role'
);

-- Policy 2: Clients can see relationships where they are the client
CREATE POLICY "clients_see_own_relationships" ON trainer_client_list
FOR SELECT
USING (
    auth.uid()::text = client_id
    OR
    -- Allow service role full access
    auth.jwt() ->> 'role' = 'service_role'
);

-- Policy 3: Trainers can update only their own relationships
CREATE POLICY "trainers_update_own_relationships" ON trainer_client_list
FOR UPDATE
USING (
    auth.uid()::text = trainer_id
    OR
    -- Allow service role full access
    auth.jwt() ->> 'role' = 'service_role'
)
WITH CHECK (
    auth.uid()::text = trainer_id
    OR
    -- Allow service role full access
    auth.jwt() ->> 'role' = 'service_role'
);

-- Policy 4: Trainers can insert relationships for themselves
CREATE POLICY "trainers_insert_own_relationships" ON trainer_client_list
FOR INSERT
WITH CHECK (
    auth.uid()::text = trainer_id
    OR
    -- Allow service role full access
    auth.jwt() ->> 'role' = 'service_role'
);

-- ============================================================================
-- IMPORTANT: Client Profile Data Separation
-- ============================================================================

-- The clients table contains SHARED profile data (all trainers can see):
-- - name, email, whatsapp
-- - experience_level, fitness_goals, health_conditions
-- - availability, preferred_training_times, dietary_preferences
-- - age, gender, status

-- The trainer_client_list table contains TRAINER-SPECIFIC data (privacy isolated):
-- - custom_price_per_session (only this trainer sees their pricing)
-- - private_notes (only this trainer sees their notes)
-- - sessions_count (session count with this specific trainer)

-- This ensures one trainer CANNOT see another trainer's:
-- 1. Custom pricing for the same client
-- 2. Private notes about the client
-- 3. Session count with that client

-- ============================================================================
-- Data Migration (if needed)
-- ============================================================================

-- If you previously stored custom_price_per_session in clients table,
-- migrate it to trainer_client_list for existing relationships
-- Uncomment below if migration is needed:

-- UPDATE trainer_client_list tcl
-- SET custom_price_per_session = c.custom_price_per_session
-- FROM clients c
-- WHERE tcl.client_id = c.client_id
--   AND c.custom_price_per_session IS NOT NULL
--   AND tcl.custom_price_per_session IS NULL;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Verify columns were added
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'trainer_client_list'
--   AND column_name IN ('custom_price_per_session', 'private_notes', 'sessions_count', 'updated_at');

-- Verify RLS policies
-- SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
-- FROM pg_policies
-- WHERE tablename = 'trainer_client_list';
