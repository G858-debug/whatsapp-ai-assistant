-- URGENT FIX: Add missing columns causing application errors
-- Run this immediately to fix the current errors

-- Fix message_history table
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS intent VARCHAR(50);
ALTER TABLE message_history ADD COLUMN IF NOT EXISTS confidence DECIMAL(3,2);

-- Fix conversation_states table  
ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS context JSONB DEFAULT '{}'::jsonb;

-- Update existing records with default values
UPDATE message_history SET intent = 'unknown' WHERE intent IS NULL;
UPDATE message_history SET confidence = 0.0 WHERE confidence IS NULL;
UPDATE conversation_states SET context = '{}'::jsonb WHERE context IS NULL;

-- Verify the fix
SELECT 'message_history columns' as table_info, column_name 
FROM information_schema.columns 
WHERE table_name = 'message_history' AND table_schema = 'public'
ORDER BY column_name;

SELECT 'conversation_states columns' as table_info, column_name 
FROM information_schema.columns 
WHERE table_name = 'conversation_states' AND table_schema = 'public'
ORDER BY column_name;