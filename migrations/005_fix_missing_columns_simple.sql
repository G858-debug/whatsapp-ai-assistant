-- Migration: Fix Missing Columns - SIMPLE VERSION
-- Description: Fixes specific column errors found in the application logs
-- Date: 2025-01-15
-- Priority: HIGH - These columns are actively being used by the application

-- ============================================
-- 1. FIX MESSAGE_HISTORY TABLE - Missing 'intent' column
-- ============================================

-- Add missing 'intent' column to message_history table
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS intent VARCHAR(50);

-- Add missing 'confidence' column to message_history table  
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS confidence DECIMAL(3,2);

-- Add index for intent column
CREATE INDEX IF NOT EXISTS idx_message_history_intent ON message_history(intent);

-- ============================================
-- 2. FIX CONVERSATION_STATES TABLE - Missing 'context' column
-- ============================================

-- Add missing 'context' column to conversation_states table
ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS context JSONB DEFAULT '{}'::jsonb;

-- Add index for context column
CREATE INDEX IF NOT EXISTS idx_conversation_states_context ON conversation_states USING gin(context);

-- ============================================
-- 3. ADD OTHER POTENTIALLY MISSING COLUMNS
-- ============================================

-- Check and add any other columns that might be missing from message_history
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS ai_intent JSONB DEFAULT '{}'::jsonb;
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS response_data JSONB DEFAULT '{}'::jsonb;

-- Check and add any other columns that might be missing from conversation_states
ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS last_intent VARCHAR(50);
ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS session_data JSONB DEFAULT '{}'::jsonb;

-- ============================================
-- 4. UPDATE EXISTING DATA (if needed)
-- ============================================

-- Set default values for existing records
UPDATE message_history SET intent = 'unknown' WHERE intent IS NULL;
UPDATE message_history SET confidence = 0.0 WHERE confidence IS NULL;
UPDATE conversation_states SET context = '{}'::jsonb WHERE context IS NULL;

-- ============================================
-- 5. ADD COMMENTS FOR DOCUMENTATION
-- ============================================

COMMENT ON COLUMN message_history.intent IS 'AI-detected intent of the message';
COMMENT ON COLUMN message_history.confidence IS 'Confidence score of the intent detection (0.0-1.0)';
COMMENT ON COLUMN conversation_states.context IS 'Additional context data for the conversation';
COMMENT ON COLUMN conversation_states.last_intent IS 'Last detected intent in this conversation';
COMMENT ON COLUMN conversation_states.session_data IS 'Session-specific data for the conversation';

-- ============================================
-- 6. SIMPLE VALIDATION - Show current columns
-- ============================================

-- Show message_history columns
SELECT 
    'message_history' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'message_history' 
AND table_schema = 'public'
AND column_name IN ('intent', 'confidence', 'ai_intent', 'response_data')
ORDER BY column_name;

-- Show conversation_states columns  
SELECT 
    'conversation_states' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'conversation_states' 
AND table_schema = 'public'
AND column_name IN ('context', 'last_intent', 'session_data')
ORDER BY column_name;

-- ============================================
-- 7. SUCCESS MESSAGE
-- ============================================

SELECT 'Migration completed successfully! The missing columns have been added.' as status;