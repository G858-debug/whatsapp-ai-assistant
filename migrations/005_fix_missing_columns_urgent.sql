-- Migration: Fix Missing Columns - URGENT
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
-- 3. VERIFY AND FIX OTHER POTENTIAL MISSING COLUMNS
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
-- 6. VALIDATION QUERY
-- ============================================

-- Check that the problematic columns now exist
DO $$
DECLARE
    missing_columns TEXT[] := ARRAY[]::TEXT[];
    column_exists BOOLEAN;
BEGIN
    -- Check message_history.intent
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'message_history' 
        AND column_name = 'intent'
        AND table_schema = 'public'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        missing_columns := array_append(missing_columns, 'message_history.intent');
    END IF;
    
    -- Check message_history.confidence
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'message_history' 
        AND column_name = 'confidence'
        AND table_schema = 'public'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        missing_columns := array_append(missing_columns, 'message_history.confidence');
    END IF;
    
    -- Check conversation_states.context
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'conversation_states' 
        AND column_name = 'context'
        AND table_schema = 'public'
    ) INTO column_exists;
    
    IF NOT column_exists THEN
        missing_columns := array_append(missing_columns, 'conversation_states.context');
    END IF;
    
    -- Report results
    IF array_length(missing_columns, 1) > 0 THEN
        RAISE EXCEPTION 'CRITICAL: Still missing columns: %', array_to_string(missing_columns, ', ');
    ELSE
        RAISE NOTICE 'SUCCESS: All critical columns are now present';
    END IF;
END $$;

-- ============================================
-- 7. SHOW CURRENT SCHEMA FOR VERIFICATION
-- ============================================

-- Show message_history columns
SELECT 
    'message_history' as table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'message_history' 
AND table_schema = 'public'
ORDER BY ordinal_position;

-- Show conversation_states columns  
SELECT 
    'conversation_states' as table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'conversation_states' 
AND table_schema = 'public'
ORDER BY ordinal_position;