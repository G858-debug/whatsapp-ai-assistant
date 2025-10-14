-- FINAL DATABASE FIX: Complete solution for all column issues
-- This addresses both missing columns and NOT NULL constraint issues

-- ============================================
-- 1. FIX MESSAGE_HISTORY TABLE
-- ============================================

-- First, add the missing columns that the code expects
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS sender VARCHAR(20);
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS intent VARCHAR(50);
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS confidence DECIMAL(3,2);

-- Copy data from existing columns to new columns
UPDATE message_history SET message = message_text WHERE message IS NULL AND message_text IS NOT NULL;
UPDATE message_history SET sender = CASE 
    WHEN direction = 'inbound' THEN 'user'
    WHEN direction = 'outbound' THEN 'bot'
    ELSE 'user'
END WHERE sender IS NULL;
UPDATE message_history SET intent = 'unknown' WHERE intent IS NULL;
UPDATE message_history SET confidence = 0.0 WHERE confidence IS NULL;

-- Make columns nullable (remove NOT NULL constraints that are causing issues)
ALTER TABLE message_history ALTER COLUMN message_text DROP NOT NULL;
ALTER TABLE message_history ALTER COLUMN direction DROP NOT NULL;

-- Update any remaining NULL values in message_text from message column
UPDATE message_history SET message_text = message WHERE message_text IS NULL AND message IS NOT NULL;

-- Set default values for direction column based on sender
UPDATE message_history SET direction = CASE 
    WHEN sender = 'user' THEN 'inbound'
    WHEN sender = 'bot' THEN 'outbound'
    ELSE 'inbound'
END WHERE direction IS NULL;

-- ============================================
-- 2. FIX CONVERSATION_STATES TABLE
-- ============================================

-- Add the missing columns that the code expects
ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS state VARCHAR(50) DEFAULT 'idle';
ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS context JSONB DEFAULT '{}'::jsonb;

-- Copy data from existing columns to new columns
UPDATE conversation_states SET state = current_state WHERE state IS NULL AND current_state IS NOT NULL;
UPDATE conversation_states SET state = 'idle' WHERE state IS NULL;
UPDATE conversation_states SET context = state_data WHERE context IS NULL AND state_data IS NOT NULL;
UPDATE conversation_states SET context = '{}'::jsonb WHERE context IS NULL;

-- ============================================
-- 3. ADD INDEXES FOR PERFORMANCE
-- ============================================

CREATE INDEX IF NOT EXISTS idx_message_history_message ON message_history(message);
CREATE INDEX IF NOT EXISTS idx_message_history_sender ON message_history(sender);
CREATE INDEX IF NOT EXISTS idx_message_history_intent ON message_history(intent);
CREATE INDEX IF NOT EXISTS idx_conversation_states_state ON conversation_states(state);
CREATE INDEX IF NOT EXISTS idx_conversation_states_context ON conversation_states USING gin(context);

-- ============================================
-- 4. VERIFICATION QUERIES
-- ============================================

-- Check message_history columns
SELECT 
    'message_history' as table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'message_history' 
AND table_schema = 'public'
AND column_name IN ('message', 'message_text', 'sender', 'direction', 'intent', 'confidence')
ORDER BY column_name;

-- Check conversation_states columns
SELECT 
    'conversation_states' as table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'conversation_states' 
AND table_schema = 'public'
AND column_name IN ('state', 'current_state', 'context', 'state_data')
ORDER BY column_name;

-- ============================================
-- 5. TEST INSERT (to verify it works)
-- ============================================

-- Test message_history insert (this should work now)
INSERT INTO message_history (phone_number, message, sender, intent, confidence, direction, message_text, message_type, processed, created_at)
VALUES ('test_phone', 'test message', 'user', 'test', 0.5, 'inbound', 'test message', 'text', false, NOW())
ON CONFLICT DO NOTHING;

-- Test conversation_states insert (this should work now)
INSERT INTO conversation_states (phone_number, state, context, created_at, updated_at)
VALUES ('test_phone_2', 'idle', '{}', NOW(), NOW())
ON CONFLICT (phone_number) DO UPDATE SET state = 'idle';

-- Clean up test data
DELETE FROM message_history WHERE phone_number = 'test_phone';
DELETE FROM conversation_states WHERE phone_number = 'test_phone_2';

SELECT 'Database fix completed successfully!' as status;