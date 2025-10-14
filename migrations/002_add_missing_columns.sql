-- Migration: Add Missing Columns to Existing Tables
-- Description: Adds columns that are referenced in the codebase but missing from current schema
-- Date: 2025-01-15

-- ============================================
-- 1. ADD MISSING COLUMNS TO TRAINERS TABLE
-- ============================================

-- Add columns that are referenced in the codebase
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS first_name VARCHAR(255);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS last_name VARCHAR(255);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS business_name VARCHAR(255);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS specialization VARCHAR(100);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS years_experience INTEGER DEFAULT 0;
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS experience_years VARCHAR(20); -- For flow compatibility
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS location VARCHAR(255);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS city VARCHAR(100); -- For flow compatibility

-- Flow-related fields
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS flow_token VARCHAR(255);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS onboarding_method VARCHAR(20) DEFAULT 'chat' CHECK (onboarding_method IN ('chat', 'flow'));
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS available_days JSONB DEFAULT '[]'::jsonb;
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS preferred_time_slots VARCHAR(50);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS notification_preferences JSONB DEFAULT '[]'::jsonb;
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE;
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS marketing_consent BOOLEAN DEFAULT FALSE;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_trainers_flow_token ON trainers(flow_token);
CREATE INDEX IF NOT EXISTS idx_trainers_onboarding_method ON trainers(onboarding_method);
CREATE INDEX IF NOT EXISTS idx_trainers_city ON trainers(city);
CREATE INDEX IF NOT EXISTS idx_trainers_specialization ON trainers(specialization);

-- ============================================
-- 2. ADD MISSING COLUMNS TO CLIENTS TABLE
-- ============================================

-- Add columns that are referenced in the codebase
ALTER TABLE clients ADD COLUMN IF NOT EXISTS fitness_goals TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS availability TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS current_package VARCHAR(50); -- For analytics compatibility

-- Convert last_session_date to DATE if it's TIMESTAMPTZ
DO $$
BEGIN
    -- Check if column exists and is TIMESTAMPTZ
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'clients' 
        AND column_name = 'last_session_date' 
        AND data_type = 'timestamp with time zone'
    ) THEN
        -- Add new DATE column
        ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_session_date_new DATE;
        
        -- Copy data converting TIMESTAMPTZ to DATE
        UPDATE clients SET last_session_date_new = last_session_date::DATE WHERE last_session_date IS NOT NULL;
        
        -- Drop old column and rename new one
        ALTER TABLE clients DROP COLUMN last_session_date;
        ALTER TABLE clients RENAME COLUMN last_session_date_new TO last_session_date;
    END IF;
END $$;

-- ============================================
-- 3. ADD MISSING COLUMNS TO BOOKINGS TABLE
-- ============================================

-- Add columns that are referenced in the codebase
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS session_date DATE;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS session_time TIME;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS session_type VARCHAR(50) DEFAULT 'one_on_one';
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS completion_notes TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS cancellation_reason TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS rescheduled_at TIMESTAMPTZ;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Update session_date and session_time from session_datetime
UPDATE bookings 
SET 
    session_date = session_datetime::DATE,
    session_time = session_datetime::TIME
WHERE session_date IS NULL OR session_time IS NULL;

-- Add missing status values to check constraint
DO $$
BEGIN
    -- Drop existing constraint
    ALTER TABLE bookings DROP CONSTRAINT IF EXISTS bookings_status_check;
    
    -- Add new constraint with all status values
    ALTER TABLE bookings ADD CONSTRAINT bookings_status_check 
        CHECK (status IN ('scheduled', 'confirmed', 'completed', 'cancelled', 'no_show', 'rescheduled'));
END $$;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(session_date);
CREATE INDEX IF NOT EXISTS idx_bookings_session_type ON bookings(session_type);

-- ============================================
-- 4. ADD MISSING COLUMNS TO HABIT_TRACKING TABLE
-- ============================================

-- Add columns that are referenced in the codebase
ALTER TABLE habit_tracking ADD COLUMN IF NOT EXISTS completed BOOLEAN DEFAULT TRUE; -- For analytics compatibility

-- ============================================
-- 5. ADD MISSING COLUMNS TO FITNESS_ASSESSMENTS TABLE
-- ============================================

-- Add columns that are referenced in the codebase (if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'fitness_assessments') THEN
        ALTER TABLE fitness_assessments ADD COLUMN IF NOT EXISTS responses JSONB DEFAULT '{}'::jsonb; -- For compatibility
        ALTER TABLE fitness_assessments ADD COLUMN IF NOT EXISTS due_date TIMESTAMPTZ;
    END IF;
END $$;

-- ============================================
-- 6. ADD MISSING COLUMNS TO PAYMENTS TABLE
-- ============================================

-- Add columns that are referenced in the codebase
ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_type VARCHAR(50); -- For analytics compatibility
ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_date TIMESTAMPTZ; -- For analytics compatibility

-- Update payment_date from paid_date if null
UPDATE payments SET payment_date = paid_date WHERE payment_date IS NULL AND paid_date IS NOT NULL;

-- ============================================
-- 7. ADD MISSING COLUMNS TO TRAINER_SUBSCRIPTIONS TABLE
-- ============================================

-- Add columns that are referenced in the codebase
ALTER TABLE trainer_subscriptions ADD COLUMN IF NOT EXISTS plan VARCHAR(50); -- For compatibility
ALTER TABLE trainer_subscriptions ADD COLUMN IF NOT EXISTS price DECIMAL(10,2);
ALTER TABLE trainer_subscriptions ADD COLUMN IF NOT EXISTS billing_cycle VARCHAR(20) DEFAULT 'monthly';
ALTER TABLE trainer_subscriptions ADD COLUMN IF NOT EXISTS payfast_token VARCHAR(255);
ALTER TABLE trainer_subscriptions ADD COLUMN IF NOT EXISTS current_period_start TIMESTAMPTZ;
ALTER TABLE trainer_subscriptions ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMPTZ;
ALTER TABLE trainer_subscriptions ADD COLUMN IF NOT EXISTS auto_renew BOOLEAN DEFAULT TRUE;
ALTER TABLE trainer_subscriptions ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ;

-- ============================================
-- 8. ADD MISSING COLUMNS TO MESSAGES TABLE
-- ============================================

-- Add columns that are referenced in the codebase
ALTER TABLE messages ADD COLUMN IF NOT EXISTS content TEXT; -- For compatibility

-- Update content from message_text if null
UPDATE messages SET content = message_text WHERE content IS NULL AND message_text IS NOT NULL;

-- ============================================
-- 9. UPDATE CHECK CONSTRAINTS
-- ============================================

-- Update clients package_type constraint to include all values used in code
DO $$
BEGIN
    -- Drop existing constraint
    ALTER TABLE clients DROP CONSTRAINT IF EXISTS clients_package_type_check;
    
    -- Add new constraint with all package types
    ALTER TABLE clients ADD CONSTRAINT clients_package_type_check 
        CHECK (package_type IN ('single', 'package_5', 'package_10', 'package_20'));
END $$;

-- Update trainers subscription_status constraint
DO $$
BEGIN
    -- Drop existing constraint
    ALTER TABLE trainers DROP CONSTRAINT IF EXISTS trainers_subscription_status_check;
    
    -- Add new constraint with all subscription statuses
    ALTER TABLE trainers ADD CONSTRAINT trainers_subscription_status_check 
        CHECK (subscription_status IN ('free', 'premium', 'pro', 'professional'));
END $$;

-- ============================================
-- 10. COMMENTS FOR NEW COLUMNS
-- ============================================

COMMENT ON COLUMN trainers.first_name IS 'Trainer first name extracted from full name';
COMMENT ON COLUMN trainers.last_name IS 'Trainer last name extracted from full name';
COMMENT ON COLUMN trainers.business_name IS 'Business or brand name';
COMMENT ON COLUMN trainers.specialization IS 'Training specialization area';
COMMENT ON COLUMN trainers.years_experience IS 'Years of training experience';
COMMENT ON COLUMN trainers.flow_token IS 'Token used for flow-based onboarding';
COMMENT ON COLUMN trainers.onboarding_method IS 'Method used for onboarding (chat or flow)';

COMMENT ON COLUMN clients.fitness_goals IS 'Client fitness goals and objectives';
COMMENT ON COLUMN clients.availability IS 'Client availability for training sessions';
COMMENT ON COLUMN clients.current_package IS 'Current package type for analytics';

COMMENT ON COLUMN bookings.session_date IS 'Date of the training session';
COMMENT ON COLUMN bookings.session_time IS 'Time of the training session';
COMMENT ON COLUMN bookings.session_type IS 'Type of training session';
COMMENT ON COLUMN bookings.completion_notes IS 'Notes added when session is completed';
COMMENT ON COLUMN bookings.cancellation_reason IS 'Reason for session cancellation';

COMMENT ON COLUMN habit_tracking.completed IS 'Whether the habit was completed (for analytics)';

COMMENT ON COLUMN payments.payment_type IS 'Type of payment for analytics';
COMMENT ON COLUMN payments.payment_date IS 'Date of payment for analytics compatibility';

COMMENT ON COLUMN messages.content IS 'Message content (compatibility field)';

-- ============================================
-- 11. CREATE MISSING INDEXES
-- ============================================

-- Additional indexes for performance
CREATE INDEX IF NOT EXISTS idx_clients_fitness_goals ON clients USING gin(to_tsvector('english', fitness_goals));
CREATE INDEX IF NOT EXISTS idx_bookings_completed_at ON bookings(completed_at);
CREATE INDEX IF NOT EXISTS idx_bookings_cancelled_at ON bookings(cancelled_at);
CREATE INDEX IF NOT EXISTS idx_payments_payment_date ON payments(payment_date);
CREATE INDEX IF NOT EXISTS idx_trainer_subscriptions_plan ON trainer_subscriptions(plan);
CREATE INDEX IF NOT EXISTS idx_trainer_subscriptions_billing_cycle ON trainer_subscriptions(billing_cycle);