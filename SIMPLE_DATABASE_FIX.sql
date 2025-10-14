-- SIMPLE DATABASE FIX: Just add missing columns and remove constraints
-- This is a minimal fix to get the application working

-- ============================================
-- 1. FIX MESSAGE_HISTORY TABLE
-- ============================================

-- Add the missing columns that the code expects
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS sender VARCHAR(20);
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS intent VARCHAR(50);
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS confidence DECIMAL(3,2);

-- Remove NOT NULL constraints that are causing issues
ALTER TABLE message_history ALTER COLUMN message_text DROP NOT NULL;
ALTER TABLE message_history ALTER COLUMN direction DROP NOT NULL;

-- Copy data from existing columns to new columns for existing records
UPDATE message_history SET message = message_text WHERE message IS NULL AND message_text IS NOT NULL;
UPDATE message_history SET sender = CASE 
    WHEN direction = 'inbound' THEN 'user'
    WHEN direction = 'outbound' THEN 'bot'
    ELSE 'user'
END WHERE sender IS NULL;
UPDATE message_history SET intent = 'unknown' WHERE intent IS NULL;
UPDATE message_history SET confidence = 0.0 WHERE confidence IS NULL;

-- Set default values for any NULL direction values
UPDATE message_history SET direction = CASE 
    WHEN sender = 'user' THEN 'inbound'
    WHEN sender = 'bot' THEN 'outbound'
    ELSE 'inbound'
END WHERE direction IS NULL;

-- Set default message_text from message if needed
UPDATE message_history SET message_text = message WHERE message_text IS NULL AND message IS NOT NULL;

-- ============================================
-- 2. FIX CONVERSATION_STATES TABLE
-- ============================================

-- Add the missing columns that the code expects
ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS state VARCHAR(50) DEFAULT 'idle';
ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS context JSONB DEFAULT '{}'::jsonb;

-- Copy data from existing columns to new columns for existing records
UPDATE conversation_states SET state = current_state WHERE state IS NULL AND current_state IS NOT NULL;
UPDATE conversation_states SET state = 'idle' WHERE state IS NULL;
UPDATE conversation_states SET context = state_data WHERE context IS NULL AND state_data IS NOT NULL;
UPDATE conversation_states SET context = '{}'::jsonb WHERE context IS NULL;

-- ============================================
-- 3. VERIFICATION (Optional - just shows what we have)
-- ============================================

-- Show the columns we now have
SELECT 'Fix completed! message_history now has these columns:' as info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'message_history' 
AND table_schema = 'public'
AND column_name IN ('message', 'message_text', 'sender', 'direction', 'intent', 'confidence')
ORDER BY column_name;

SELECT 'conversation_states now has these columns:' as info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'conversation_states' 
AND table_schema = 'public'
AND column_name IN ('state', 'current_state', 'context', 'state_data')
ORDER BY column_name;