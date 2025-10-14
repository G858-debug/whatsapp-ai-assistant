-- ============================================
-- DIAGNOSTIC SCRIPT: Check Missing Columns
-- Description: Diagnoses which columns are missing based on error logs
-- Date: 2025-01-15
-- ============================================

-- This script checks for the specific columns mentioned in your error logs

\echo 'Checking for missing columns that are causing application errors...'

-- ============================================
-- 1. CHECK MESSAGE_HISTORY TABLE
-- ============================================
\echo 'Checking message_history table...'

SELECT 
    'message_history' as table_name,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'message_history' 
            AND column_name = 'intent'
            AND table_schema = 'public'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as intent_column,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'message_history' 
            AND column_name = 'confidence'
            AND table_schema = 'public'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as confidence_column,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'message_history' 
            AND column_name = 'ai_intent'
            AND table_schema = 'public'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as ai_intent_column,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'message_history' 
            AND column_name = 'response_data'
            AND table_schema = 'public'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as response_data_column;

-- ============================================
-- 2. CHECK CONVERSATION_STATES TABLE
-- ============================================
\echo 'Checking conversation_states table...'

SELECT 
    'conversation_states' as table_name,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'conversation_states' 
            AND column_name = 'context'
            AND table_schema = 'public'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as context_column,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'conversation_states' 
            AND column_name = 'state_data'
            AND table_schema = 'public'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as state_data_column,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'conversation_states' 
            AND column_name = 'current_state'
            AND table_schema = 'public'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as current_state_column;

-- ============================================
-- 3. CHECK IF TABLES EXIST
-- ============================================
\echo 'Checking if required tables exist...'

SELECT 
    'Table Existence Check' as check_type,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'message_history'
            AND table_schema = 'public'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as message_history_table,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'conversation_states'
            AND table_schema = 'public'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as conversation_states_table,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'processed_messages'
            AND table_schema = 'public'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as processed_messages_table;

-- ============================================
-- 4. SHOW ACTUAL COLUMNS IN PROBLEMATIC TABLES
-- ============================================
\echo 'Current columns in message_history table:'

SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'message_history' 
AND table_schema = 'public'
ORDER BY ordinal_position;

\echo 'Current columns in conversation_states table:'

SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'conversation_states' 
AND table_schema = 'public'
ORDER BY ordinal_position;

-- ============================================
-- 5. GENERATE FIX COMMANDS
-- ============================================
\echo 'If any columns are missing, run these commands:'

SELECT 
    'Fix Commands' as info,
    'ALTER TABLE message_history ADD COLUMN IF NOT EXISTS intent VARCHAR(50);' as fix_intent,
    'ALTER TABLE message_history ADD COLUMN IF NOT EXISTS confidence DECIMAL(3,2);' as fix_confidence,
    'ALTER TABLE conversation_states ADD COLUMN IF NOT EXISTS context JSONB DEFAULT ''{}''::jsonb;' as fix_context;