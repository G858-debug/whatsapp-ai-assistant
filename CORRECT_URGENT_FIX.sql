-- CORRECT URGENT FIX: Add the actual missing columns based on code analysis
-- Run this immediately to fix the current errors

-- Fix message_history table - add the columns the code is actually looking for
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS sender VARCHAR(20);
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS intent VARCHAR(50);
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS confidence DECIMAL(3,2);

-- Fix conversation_states table - add the columns the code is actually looking for  
ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS state VARCHAR(50) DEFAULT 'idle';
ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS context JSONB DEFAULT '{}'::jsonb;

-- Update existing records with default values
UPDATE message_history SET message = message_text WHERE message IS NULL AND message_text IS NOT NULL;
UPDATE message_history SET sender = CASE 
    WHEN direction = 'inbound' THEN 'user'
    WHEN direction = 'outbound' THEN 'bot'
    ELSE 'user'
END WHERE sender IS NULL;
UPDATE message_history SET intent = 'unknown' WHERE intent IS NULL;
UPDATE message_history SET confidence = 0.0 WHERE confidence IS NULL;

UPDATE conversation_states SET state = current_state WHERE state IS NULL AND current_state IS NOT NULL;
UPDATE conversation_states SET state = 'idle' WHERE state IS NULL;
UPDATE conversation_states SET context = state_data WHERE context IS NULL AND state_data IS NOT NULL;
UPDATE conversation_states SET context = '{}'::jsonb WHERE context IS NULL;

-- Verify the fix
SELECT 'message_history columns' as table_info, column_name 
FROM information_schema.columns 
WHERE table_name = 'message_history' AND table_schema = 'public'
AND column_name IN ('message', 'sender', 'intent', 'confidence')
ORDER BY column_name;

SELECT 'conversation_states columns' as table_info, column_name 
FROM information_schema.columns 
WHERE table_name = 'conversation_states' AND table_schema = 'public'
AND column_name IN ('state', 'context', 'current_state')
ORDER BY column_name;