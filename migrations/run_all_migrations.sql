-- ============================================
-- RUN ALL MIGRATIONS SCRIPT
-- Description: Executes all migration scripts in the correct order
-- Date: 2025-01-15
-- ============================================

-- This script runs all migrations to bring your Supabase database
-- up to date with all the database interactions found in your codebase

BEGIN;

-- ============================================
-- MIGRATION 1: Add Missing Core Tables
-- ============================================
\echo 'Running Migration 1: Add Missing Core Tables...'

-- Include the content of 001_add_missing_core_tables.sql
\i migrations/001_add_missing_core_tables.sql

-- ============================================
-- MIGRATION 2: Add Missing Columns
-- ============================================
\echo 'Running Migration 2: Add Missing Columns...'

-- Include the content of 002_add_missing_columns.sql
\i migrations/002_add_missing_columns.sql

-- ============================================
-- MIGRATION 3: Add Calendar and Gamification Tables
-- ============================================
\echo 'Running Migration 3: Add Calendar and Gamification Tables...'

-- Include the content of 003_add_calendar_gamification_tables.sql
\i migrations/003_add_calendar_gamification_tables.sql

-- ============================================
-- MIGRATION 4: Add Registration Sessions Compatibility
-- ============================================
\echo 'Running Migration 4: Add Registration Sessions Compatibility...'

-- Include the content of 004_add_registration_sessions_compatibility.sql
\i migrations/004_add_registration_sessions_compatibility.sql

-- ============================================
-- FINAL VALIDATION
-- ============================================
\echo 'Running Final Validation...'

-- Check that all expected tables exist
DO $$
DECLARE
    missing_tables TEXT[] := ARRAY[]::TEXT[];
    table_name TEXT;
    expected_tables TEXT[] := ARRAY[
        'registration_analytics',
        'registration_attempts', 
        'habit_goals',
        'analytics_events',
        'activity_logs',
        'dashboard_stats',
        'dashboard_notifications',
        'dashboard_tokens',
        'calendar_sync_preferences',
        'calendar_sync_status',
        'calendar_events',
        'gamification_points',
        'achievements',
        'leaderboards',
        'trainers_archive',
        'clients_archive',
        'registration_sessions'
    ];
BEGIN
    -- Check each expected table
    FOREACH table_name IN ARRAY expected_tables
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = table_name AND table_schema = 'public'
        ) THEN
            missing_tables := array_append(missing_tables, table_name);
        END IF;
    END LOOP;
    
    -- Report results
    IF array_length(missing_tables, 1) > 0 THEN
        RAISE NOTICE 'WARNING: Missing tables: %', array_to_string(missing_tables, ', ');
    ELSE
        RAISE NOTICE 'SUCCESS: All expected tables are present';
    END IF;
    
    -- Count total tables
    RAISE NOTICE 'Total tables in database: %', (
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    );
END $$;

-- Check that key columns exist
DO $$
DECLARE
    missing_columns TEXT[] := ARRAY[]::TEXT[];
    column_check RECORD;
    expected_columns RECORD[] := ARRAY[
        ROW('trainers', 'first_name'),
        ROW('trainers', 'business_name'),
        ROW('trainers', 'specialization'),
        ROW('trainers', 'flow_token'),
        ROW('clients', 'fitness_goals'),
        ROW('clients', 'current_package'),
        ROW('bookings', 'session_date'),
        ROW('bookings', 'session_type'),
        ROW('habit_tracking', 'completed'),
        ROW('payments', 'payment_type'),
        ROW('messages', 'content')
    ]::RECORD[];
BEGIN
    -- Check each expected column
    FOREACH column_check IN ARRAY expected_columns
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = (column_check).f1 
            AND column_name = (column_check).f2
            AND table_schema = 'public'
        ) THEN
            missing_columns := array_append(missing_columns, (column_check).f1 || '.' || (column_check).f2);
        END IF;
    END LOOP;
    
    -- Report results
    IF array_length(missing_columns, 1) > 0 THEN
        RAISE NOTICE 'WARNING: Missing columns: %', array_to_string(missing_columns, ', ');
    ELSE
        RAISE NOTICE 'SUCCESS: All expected columns are present';
    END IF;
END $$;

-- ============================================
-- MIGRATION COMPLETE
-- ============================================
\echo 'All migrations completed successfully!'
\echo 'Your database now includes all tables and columns referenced in your codebase.'

COMMIT;

-- ============================================
-- POST-MIGRATION NOTES
-- ============================================
/*
POST-MIGRATION CHECKLIST:

1. ✅ Core missing tables added:
   - registration_analytics
   - registration_attempts  
   - habit_goals
   - analytics_events
   - activity_logs
   - dashboard_stats
   - dashboard_notifications
   - dashboard_tokens

2. ✅ Calendar sync tables added:
   - calendar_sync_preferences
   - calendar_sync_status
   - calendar_events

3. ✅ Gamification tables added:
   - gamification_points
   - achievements
   - leaderboards

4. ✅ Archive tables added:
   - trainers_archive
   - clients_archive

5. ✅ Compatibility tables added:
   - registration_sessions

6. ✅ Missing columns added to existing tables:
   - trainers: first_name, business_name, specialization, flow_token, etc.
   - clients: fitness_goals, current_package
   - bookings: session_date, session_type, completion_notes, etc.
   - habit_tracking: completed
   - payments: payment_type, payment_date
   - messages: content

7. ✅ Indexes created for performance
8. ✅ RLS policies applied
9. ✅ Triggers for updated_at columns
10. ✅ Cleanup functions created
11. ✅ Scheduled jobs configured (if pg_cron available)

NEXT STEPS:
1. Test your application to ensure all database interactions work
2. Run your existing tests to verify compatibility
3. Monitor performance and adjust indexes if needed
4. Consider removing unused tables from the current schema if they're not needed

ROLLBACK INSTRUCTIONS:
If you need to rollback these changes, you can:
1. Drop the new tables: DROP TABLE IF EXISTS table_name CASCADE;
2. Remove the new columns: ALTER TABLE table_name DROP COLUMN IF EXISTS column_name;
3. Restore original constraints if modified

BACKUP RECOMMENDATION:
Always backup your database before running migrations in production!
*/