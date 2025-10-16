-- ============================================
-- DUAL ROLE USER SUPPORT MIGRATION
-- ============================================
-- This migration adds support for users who are both trainers and clients
-- by adding a role_preference column to conversation_states table

-- Add role_preference column to conversation_states table
ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS role_preference VARCHAR(20) DEFAULT NULL;

-- Add index for better performance on role preference queries
CREATE INDEX IF NOT EXISTS idx_conversation_states_role_preference ON conversation_states(role_preference);

-- Add comments for documentation
COMMENT ON COLUMN conversation_states.role_preference IS 'Stores the preferred role (trainer/client) for dual-role users';

-- Verify the changes
SELECT 'conversation_states role_preference column added' as status;

SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'conversation_states' 
AND table_schema = 'public'
AND column_name = 'role_preference'
ORDER BY column_name;