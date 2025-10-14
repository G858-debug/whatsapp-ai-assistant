-- ============================================
-- FINAL SUPABASE DATABASE SCHEMA
-- Comprehensive schema based on all backend database interactions
-- Generated from complete codebase analysis
-- Date: 2025-01-15
-- ============================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- ============================================
-- 1. CORE USER TABLES
-- ============================================

-- Trainers table
CREATE TABLE IF NOT EXISTS trainers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    whatsapp VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    business_name VARCHAR(255),
    specialization VARCHAR(100),
    years_experience INTEGER DEFAULT 0,
    experience_years VARCHAR(20), -- For flow compatibility
    location VARCHAR(255),
    city VARCHAR(100), -- For flow compatibility
    pricing_per_session DECIMAL(10,2) DEFAULT 500.00,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    subscription_status VARCHAR(50) DEFAULT 'free' CHECK (subscription_status IN ('free', 'premium', 'pro', 'professional')),
    subscription_expires_at TIMESTAMPTZ,
    subscription_end TIMESTAMPTZ, -- For test compatibility
    
    -- Flow-related fields
    flow_token VARCHAR(255),
    onboarding_method VARCHAR(20) DEFAULT 'chat' CHECK (onboarding_method IN ('chat', 'flow')),
    available_days JSONB DEFAULT '[]'::jsonb,
    preferred_time_slots VARCHAR(50),
    notification_preferences JSONB DEFAULT '[]'::jsonb,
    terms_accepted BOOLEAN DEFAULT FALSE,
    marketing_consent BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Clients table
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    whatsapp VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    fitness_goals TEXT,
    availability TEXT,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    package_type VARCHAR(50) DEFAULT 'single' CHECK (package_type IN ('single', 'package_5', 'package_10', 'package_20')),
    current_package VARCHAR(50), -- For analytics compatibility
    sessions_remaining INTEGER DEFAULT 1,
    custom_price_per_session DECIMAL(10,2),
    last_session_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique client per trainer
    CONSTRAINT unique_client_per_trainer UNIQUE (trainer_id, whatsapp)
);

-- ============================================
-- 2. BOOKING AND SESSION TABLES
-- ============================================

-- Bookings table
CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    session_datetime TIMESTAMPTZ NOT NULL,
    session_date DATE NOT NULL, -- For compatibility
    session_time TIME, -- For compatibility
    duration_minutes INTEGER DEFAULT 60,
    price DECIMAL(10,2) NOT NULL,
    session_type VARCHAR(50) DEFAULT 'one_on_one',
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'confirmed', 'completed', 'cancelled', 'no_show', 'rescheduled')),
    notes TEXT,
    session_notes TEXT,
    completion_notes TEXT,
    cancellation_reason TEXT,
    cancelled_at TIMESTAMPTZ,
    rescheduled_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 3. HABIT TRACKING TABLES
-- ============================================

-- Habit tracking table (main)
CREATE TABLE IF NOT EXISTS habit_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    habit_type VARCHAR(50) NOT NULL CHECK (habit_type IN (
        'water_intake', 'sleep_hours', 'steps', 'calories', 
        'workout_completed', 'meals_logged', 'weight', 'mood'
    )),
    value TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    completed BOOLEAN DEFAULT TRUE, -- For analytics compatibility
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one entry per client per habit type per day
    CONSTRAINT unique_habit_per_day UNIQUE (client_id, habit_type, date)
);

-- Habits table (for test compatibility)
CREATE TABLE IF NOT EXISTS habits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    habit_type VARCHAR(50) NOT NULL CHECK (habit_type IN (
        'water_intake', 'sleep_hours', 'steps', 'calories', 
        'workout_completed', 'meals_logged', 'weight', 'mood'
    )),
    value TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Habit goals table
CREATE TABLE IF NOT EXISTS habit_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    habit_type VARCHAR(50) NOT NULL,
    goal_value TEXT NOT NULL,
    goal_type VARCHAR(20) DEFAULT 'daily' CHECK (goal_type IN ('daily', 'weekly', 'monthly')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 4. ASSESSMENT TABLES
-- ============================================

-- Assessment templates
CREATE TABLE IF NOT EXISTS assessment_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    template_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    completed_by VARCHAR(20) DEFAULT 'client' CHECK (completed_by IN ('client', 'trainer')),
    frequency VARCHAR(20) DEFAULT 'quarterly' CHECK (frequency IN ('weekly', 'monthly', 'quarterly', 'annually')),
    sections JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fitness assessments
CREATE TABLE IF NOT EXISTS fitness_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    template_id UUID REFERENCES assessment_templates(id) ON DELETE SET NULL,
    assessment_type VARCHAR(50) DEFAULT 'progress' CHECK (assessment_type IN ('initial', 'progress', 'final')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled')),
    questions JSONB DEFAULT '{}'::jsonb,
    answers JSONB DEFAULT '{}'::jsonb,
    responses JSONB DEFAULT '{}'::jsonb, -- For compatibility
    score DECIMAL(5,2),
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Assessments table (for compatibility)
CREATE TABLE IF NOT EXISTS assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    assessment_type VARCHAR(50) NOT NULL CHECK (assessment_type IN ('initial', 'progress', 'final')),
    questions JSONB NOT NULL DEFAULT '{}',
    answers JSONB NOT NULL DEFAULT '{}',
    score DECIMAL(5,2),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 5. WORKOUT TABLES
-- ============================================

-- Workouts table
CREATE TABLE IF NOT EXISTS workouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    workout_type VARCHAR(50) DEFAULT 'general' CHECK (workout_type IN ('strength', 'cardio', 'flexibility', 'general')),
    duration_minutes INTEGER DEFAULT 60,
    difficulty_level VARCHAR(20) DEFAULT 'medium' CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    exercises JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 6. MESSAGING TABLES
-- ============================================

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID REFERENCES trainers(id),
    client_id UUID REFERENCES clients(id),
    phone_number VARCHAR(20) NOT NULL,
    message_text TEXT NOT NULL,
    content TEXT, -- For compatibility
    message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'audio', 'video', 'document')),
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Message history table
CREATE TABLE IF NOT EXISTS message_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL,
    message_text TEXT NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'audio', 'document')),
    processed BOOLEAN DEFAULT FALSE,
    intent VARCHAR(50),
    confidence DECIMAL(3,2),
    ai_intent JSONB DEFAULT '{}'::jsonb,
    response_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation states table
CREATE TABLE IF NOT EXISTS conversation_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    current_state VARCHAR(50) DEFAULT 'idle',
    state_data JSONB DEFAULT '{}'::jsonb,
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 7. REGISTRATION TABLES
-- ============================================

-- Registration states table
CREATE TABLE IF NOT EXISTS registration_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    current_step INTEGER DEFAULT 0,
    data JSONB DEFAULT '{}'::jsonb,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Registration sessions table (for compatibility)
CREATE TABLE IF NOT EXISTS registration_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    registration_type VARCHAR(20) NOT NULL CHECK (registration_type IN ('trainer', 'client', 'unknown')),
    step VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'in_progress', 'completed', 'expired', 'cancelled', 'abandoned', 'error')),
    data JSONB DEFAULT '{}'::jsonb,
    retry_count INTEGER DEFAULT 0,
    needs_retry BOOLEAN DEFAULT FALSE,
    last_error_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Registration analytics table
CREATE TABLE IF NOT EXISTS registration_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'started', 'step_completed', 'validation_error', 'completed', 'abandoned', 'system_error', 'already_registered'
    step_number INTEGER,
    user_type VARCHAR(20) CHECK (user_type IN ('trainer', 'client')),
    error_field VARCHAR(50),
    error_message TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Registration attempts table
CREATE TABLE IF NOT EXISTS registration_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) NOT NULL,
    user_type VARCHAR(20) CHECK (user_type IN ('trainer', 'client')),
    existing_user_id UUID,
    attempt_type VARCHAR(50) CHECK (attempt_type IN ('new', 'duplicate', 'retry', 'abandoned')),
    attempt_data JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 8. WHATSAPP FLOW TABLES
-- ============================================

-- Flow tokens table
CREATE TABLE IF NOT EXISTS flow_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL,
    flow_token VARCHAR(255) NOT NULL UNIQUE,
    flow_type VARCHAR(50) NOT NULL CHECK (flow_type IN ('trainer_onboarding', 'client_onboarding', 'assessment_flow', 'booking_flow')),
    flow_data JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'expired', 'cancelled')),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Flow responses table
CREATE TABLE IF NOT EXISTS flow_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_token VARCHAR(255) NOT NULL REFERENCES flow_tokens(flow_token) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    flow_type VARCHAR(50) NOT NULL,
    response_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    screen_id VARCHAR(100),
    completed BOOLEAN DEFAULT FALSE,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 9. PAYMENT TABLES
-- ============================================

-- Payment requests table
CREATE TABLE IF NOT EXISTS payment_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'cancelled', 'expired')),
    transaction_id VARCHAR(100),
    payment_id UUID,
    payfast_payment_id VARCHAR(100),
    payment_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    payment_request_id UUID REFERENCES payment_requests(id),
    amount DECIMAL(10,2) NOT NULL,
    processor_fee DECIMAL(10,2) DEFAULT 0,
    net_amount DECIMAL(10,2),
    payment_method VARCHAR(50) DEFAULT 'payfast',
    payment_type VARCHAR(50), -- For analytics compatibility
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'completed', 'failed', 'cancelled')),
    payment_date TIMESTAMPTZ, -- For analytics compatibility
    paid_date TIMESTAMPTZ,
    payfast_payment_id VARCHAR(100),
    payfast_payment_status VARCHAR(50),
    webhook_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Client payment tokens table
CREATE TABLE IF NOT EXISTS client_payment_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    payfast_token VARCHAR(255),
    payfast_token_status VARCHAR(20) DEFAULT 'active' CHECK (payfast_token_status IN ('active', 'inactive', 'expired')),
    card_last_four VARCHAR(4),
    card_brand VARCHAR(20),
    consent_given BOOLEAN DEFAULT FALSE,
    consent_date TIMESTAMPTZ,
    consent_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Token setup requests table
CREATE TABLE IF NOT EXISTS token_setup_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    setup_code VARCHAR(20) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'expired', 'cancelled')),
    token_id UUID,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- PayFast webhooks table
CREATE TABLE IF NOT EXISTS payfast_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_type VARCHAR(50) NOT NULL,
    event_type VARCHAR(50),
    payfast_payment_id VARCHAR(100),
    payload JSONB NOT NULL,
    signature VARCHAR(255),
    signature_valid BOOLEAN,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 10. SUBSCRIPTION TABLES
-- ============================================

-- Subscription plans table
CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price_monthly DECIMAL(10,2) NOT NULL,
    price_annual DECIMAL(10,2),
    features JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trainer subscriptions table
CREATE TABLE IF NOT EXISTS trainer_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES subscription_plans(id),
    plan VARCHAR(50), -- For compatibility
    status VARCHAR(50) NOT NULL CHECK (status IN ('active', 'inactive', 'cancelled', 'expired')),
    price DECIMAL(10,2),
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    payfast_token VARCHAR(255),
    payfast_subscription_id VARCHAR(100),
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    auto_renew BOOLEAN DEFAULT TRUE,
    cancelled_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subscription payment history table
CREATE TABLE IF NOT EXISTS subscription_payment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    subscription_id UUID NOT NULL REFERENCES trainer_subscriptions(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    fee_amount DECIMAL(10,2) DEFAULT 0,
    net_amount DECIMAL(10,2),
    payment_status VARCHAR(20) DEFAULT 'pending',
    payfast_payment_id VARCHAR(100),
    payfast_payment_status VARCHAR(50),
    webhook_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 11. ANALYTICS TABLES
-- ============================================

-- Analytics events table
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    metadata JSONB DEFAULT '{}'::jsonb,
    device_info JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Activity logs table
CREATE TABLE IF NOT EXISTS activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    activity_type VARCHAR(50) NOT NULL,
    activity_data JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 12. DASHBOARD TABLES
-- ============================================

-- Dashboard stats table
CREATE TABLE IF NOT EXISTS dashboard_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID REFERENCES trainers(id) ON DELETE CASCADE,
    stat_date DATE NOT NULL,
    total_clients INTEGER DEFAULT 0,
    active_clients INTEGER DEFAULT 0,
    sessions_completed INTEGER DEFAULT 0,
    sessions_cancelled INTEGER DEFAULT 0,
    revenue_amount DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dashboard notifications table
CREATE TABLE IF NOT EXISTS dashboard_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    notification_type VARCHAR(50),
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dashboard tokens table
CREATE TABLE IF NOT EXISTS dashboard_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 13. CALENDAR SYNC TABLES
-- ============================================

-- Calendar sync preferences table
CREATE TABLE IF NOT EXISTS calendar_sync_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    google_calendar_enabled BOOLEAN DEFAULT FALSE,
    outlook_calendar_enabled BOOLEAN DEFAULT FALSE,
    sync_frequency VARCHAR(20) DEFAULT 'hourly',
    auto_create_events BOOLEAN DEFAULT TRUE,
    event_title_template VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Calendar sync status table
CREATE TABLE IF NOT EXISTS calendar_sync_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL,
    last_sync TIMESTAMPTZ,
    sync_status VARCHAR(20) DEFAULT 'pending',
    events_synced INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Calendar events table
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    external_event_id VARCHAR(255) NOT NULL,
    provider VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 14. GAMIFICATION TABLES
-- ============================================

-- Gamification points table
CREATE TABLE IF NOT EXISTS gamification_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    points INTEGER NOT NULL DEFAULT 0,
    reason VARCHAR(100) NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    activity_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Achievements table
CREATE TABLE IF NOT EXISTS achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    achievement_type VARCHAR(50) NOT NULL,
    achievement_name VARCHAR(100) NOT NULL,
    description TEXT,
    points_awarded INTEGER DEFAULT 0,
    unlocked_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Leaderboards table
CREATE TABLE IF NOT EXISTS leaderboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    leaderboard_type VARCHAR(50) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    rankings JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Challenge progress table
CREATE TABLE IF NOT EXISTS challenge_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    challenge_type VARCHAR(50) NOT NULL,
    challenge_name VARCHAR(100) NOT NULL,
    target_value INTEGER NOT NULL,
    current_value INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'failed', 'paused')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 15. ARCHIVE TABLES
-- ============================================

-- Trainers archive table
CREATE TABLE IF NOT EXISTS trainers_archive (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    whatsapp VARCHAR(20),
    business_name VARCHAR(255),
    location VARCHAR(255),
    specialization VARCHAR(255),
    pricing_per_session DECIMAL(10,2),
    status VARCHAR(20),
    subscription_status VARCHAR(50),
    subscription_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ DEFAULT NOW(),
    merge_target_id UUID,
    archive_reason VARCHAR(50)
);

-- Clients archive table
CREATE TABLE IF NOT EXISTS clients_archive (
    id UUID PRIMARY KEY,
    trainer_id UUID,
    name VARCHAR(255),
    email VARCHAR(255),
    whatsapp VARCHAR(20),
    fitness_goals TEXT,
    availability TEXT,
    sessions_remaining INTEGER,
    package_type VARCHAR(50),
    custom_price_per_session DECIMAL(10,2),
    status VARCHAR(20),
    created_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ DEFAULT NOW(),
    merge_target_id UUID,
    archive_reason VARCHAR(50)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Trainers indexes
CREATE INDEX IF NOT EXISTS idx_trainers_whatsapp ON trainers(whatsapp);
CREATE INDEX IF NOT EXISTS idx_trainers_email ON trainers(LOWER(email));
CREATE INDEX IF NOT EXISTS idx_trainers_status ON trainers(status);
CREATE INDEX IF NOT EXISTS idx_trainers_subscription_status ON trainers(subscription_status);
CREATE INDEX IF NOT EXISTS idx_trainers_flow_token ON trainers(flow_token);
CREATE INDEX IF NOT EXISTS idx_trainers_onboarding_method ON trainers(onboarding_method);
CREATE INDEX IF NOT EXISTS idx_trainers_city ON trainers(city);
CREATE INDEX IF NOT EXISTS idx_trainers_specialization ON trainers(specialization);

-- Clients indexes
CREATE INDEX IF NOT EXISTS idx_clients_trainer ON clients(trainer_id);
CREATE INDEX IF NOT EXISTS idx_clients_whatsapp ON clients(whatsapp);
CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(LOWER(email));
CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);
CREATE INDEX IF NOT EXISTS idx_clients_last_session ON clients(last_session_date);

-- Bookings indexes
CREATE INDEX IF NOT EXISTS idx_bookings_trainer ON bookings(trainer_id);
CREATE INDEX IF NOT EXISTS idx_bookings_client ON bookings(client_id);
CREATE INDEX IF NOT EXISTS idx_bookings_datetime ON bookings(session_datetime);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(session_date);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);

-- Habit tracking indexes
CREATE INDEX IF NOT EXISTS idx_habit_tracking_client ON habit_tracking(client_id);
CREATE INDEX IF NOT EXISTS idx_habit_tracking_date ON habit_tracking(date);
CREATE INDEX IF NOT EXISTS idx_habit_tracking_type ON habit_tracking(habit_type);
CREATE INDEX IF NOT EXISTS idx_habit_tracking_client_date ON habit_tracking(client_id, date);

-- Habits table indexes (compatibility)
CREATE INDEX IF NOT EXISTS idx_habits_trainer ON habits(trainer_id);
CREATE INDEX IF NOT EXISTS idx_habits_client ON habits(client_id);
CREATE INDEX IF NOT EXISTS idx_habits_date ON habits(date);
CREATE INDEX IF NOT EXISTS idx_habits_type ON habits(habit_type);

-- Messages indexes
CREATE INDEX IF NOT EXISTS idx_messages_phone ON messages(phone_number);
CREATE INDEX IF NOT EXISTS idx_messages_trainer ON messages(trainer_id);
CREATE INDEX IF NOT EXISTS idx_messages_client ON messages(client_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_processed ON messages(processed);

-- Message history indexes
CREATE INDEX IF NOT EXISTS idx_message_history_phone ON message_history(phone_number);
CREATE INDEX IF NOT EXISTS idx_message_history_direction ON message_history(direction);
CREATE INDEX IF NOT EXISTS idx_message_history_created ON message_history(created_at);
CREATE INDEX IF NOT EXISTS idx_message_history_processed ON message_history(processed);

-- Conversation states indexes
CREATE INDEX IF NOT EXISTS idx_conversation_states_phone ON conversation_states(phone_number);
CREATE INDEX IF NOT EXISTS idx_conversation_states_state ON conversation_states(current_state);
CREATE INDEX IF NOT EXISTS idx_conversation_states_activity ON conversation_states(last_activity);

-- Registration indexes
CREATE INDEX IF NOT EXISTS idx_registration_states_phone ON registration_states(phone_number);
CREATE INDEX IF NOT EXISTS idx_registration_states_user_type ON registration_states(user_type);
CREATE INDEX IF NOT EXISTS idx_registration_states_completed ON registration_states(completed);

CREATE INDEX IF NOT EXISTS idx_registration_sessions_phone ON registration_sessions(phone);
CREATE INDEX IF NOT EXISTS idx_registration_sessions_status ON registration_sessions(status);
CREATE INDEX IF NOT EXISTS idx_registration_sessions_expires ON registration_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_registration_sessions_needs_retry ON registration_sessions(needs_retry) WHERE needs_retry = TRUE;

CREATE INDEX IF NOT EXISTS idx_registration_analytics_phone ON registration_analytics(phone_number);
CREATE INDEX IF NOT EXISTS idx_registration_analytics_event ON registration_analytics(event_type);
CREATE INDEX IF NOT EXISTS idx_registration_analytics_timestamp ON registration_analytics(timestamp);

CREATE INDEX IF NOT EXISTS idx_registration_attempts_phone ON registration_attempts(phone);
CREATE INDEX IF NOT EXISTS idx_registration_attempts_user ON registration_attempts(existing_user_id);
CREATE INDEX IF NOT EXISTS idx_registration_attempts_created ON registration_attempts(created_at);

-- Flow indexes
CREATE INDEX IF NOT EXISTS idx_flow_tokens_phone ON flow_tokens(phone_number);
CREATE INDEX IF NOT EXISTS idx_flow_tokens_token ON flow_tokens(flow_token);
CREATE INDEX IF NOT EXISTS idx_flow_tokens_type ON flow_tokens(flow_type);
CREATE INDEX IF NOT EXISTS idx_flow_tokens_status ON flow_tokens(status);
CREATE INDEX IF NOT EXISTS idx_flow_tokens_created ON flow_tokens(created_at);

CREATE INDEX IF NOT EXISTS idx_flow_responses_token ON flow_responses(flow_token);
CREATE INDEX IF NOT EXISTS idx_flow_responses_phone ON flow_responses(phone_number);
CREATE INDEX IF NOT EXISTS idx_flow_responses_type ON flow_responses(flow_type);
CREATE INDEX IF NOT EXISTS idx_flow_responses_completed ON flow_responses(completed);
CREATE INDEX IF NOT EXISTS idx_flow_responses_processed ON flow_responses(processed);

-- Payment indexes
CREATE INDEX IF NOT EXISTS idx_payment_requests_trainer ON payment_requests(trainer_id);
CREATE INDEX IF NOT EXISTS idx_payment_requests_client ON payment_requests(client_id);
CREATE INDEX IF NOT EXISTS idx_payment_requests_status ON payment_requests(status);
CREATE INDEX IF NOT EXISTS idx_payment_requests_transaction_id ON payment_requests(transaction_id);

CREATE INDEX IF NOT EXISTS idx_payments_trainer ON payments(trainer_id);
CREATE INDEX IF NOT EXISTS idx_payments_client ON payments(client_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);
CREATE INDEX IF NOT EXISTS idx_payments_payfast_id ON payments(payfast_payment_id);

CREATE INDEX IF NOT EXISTS idx_payment_tokens_client ON client_payment_tokens(client_id);
CREATE INDEX IF NOT EXISTS idx_payment_tokens_trainer ON client_payment_tokens(trainer_id);
CREATE INDEX IF NOT EXISTS idx_payment_tokens_status ON client_payment_tokens(payfast_token_status);

CREATE INDEX IF NOT EXISTS idx_token_setup_trainer ON token_setup_requests(trainer_id);
CREATE INDEX IF NOT EXISTS idx_token_setup_client ON token_setup_requests(client_id);
CREATE INDEX IF NOT EXISTS idx_token_setup_code ON token_setup_requests(setup_code);
CREATE INDEX IF NOT EXISTS idx_token_setup_status ON token_setup_requests(status);

-- Subscription indexes
CREATE INDEX IF NOT EXISTS idx_subscription_plans_code ON subscription_plans(plan_code);
CREATE INDEX IF NOT EXISTS idx_trainer_subs_trainer_id ON trainer_subscriptions(trainer_id);
CREATE INDEX IF NOT EXISTS idx_trainer_subs_status ON trainer_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_trainer_subs_plan ON trainer_subscriptions(plan_id);

-- Analytics indexes
CREATE INDEX IF NOT EXISTS idx_analytics_events_user ON analytics_events(user_id, user_type);
CREATE INDEX IF NOT EXISTS idx_analytics_events_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_events_timestamp ON analytics_events(timestamp);

CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id, user_type);
CREATE INDEX IF NOT EXISTS idx_activity_logs_type ON activity_logs(activity_type);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON activity_logs(created_at);

-- Assessment indexes
CREATE INDEX IF NOT EXISTS idx_assessment_templates_trainer ON assessment_templates(trainer_id);
CREATE INDEX IF NOT EXISTS idx_assessment_templates_active ON assessment_templates(is_active);

CREATE INDEX IF NOT EXISTS idx_fitness_assessments_trainer ON fitness_assessments(trainer_id);
CREATE INDEX IF NOT EXISTS idx_fitness_assessments_client ON fitness_assessments(client_id);
CREATE INDEX IF NOT EXISTS idx_fitness_assessments_template ON fitness_assessments(template_id);
CREATE INDEX IF NOT EXISTS idx_fitness_assessments_status ON fitness_assessments(status);

CREATE INDEX IF NOT EXISTS idx_assessments_client ON assessments(client_id);
CREATE INDEX IF NOT EXISTS idx_assessments_type ON assessments(assessment_type);
CREATE INDEX IF NOT EXISTS idx_assessments_completed ON assessments(completed_at);

-- Workout indexes
CREATE INDEX IF NOT EXISTS idx_workouts_trainer ON workouts(trainer_id);
CREATE INDEX IF NOT EXISTS idx_workouts_client ON workouts(client_id);
CREATE INDEX IF NOT EXISTS idx_workouts_type ON workouts(workout_type);
CREATE INDEX IF NOT EXISTS idx_workouts_difficulty ON workouts(difficulty_level);

-- Dashboard indexes
CREATE INDEX IF NOT EXISTS idx_dashboard_stats_trainer ON dashboard_stats(trainer_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_stats_date ON dashboard_stats(stat_date);
CREATE INDEX IF NOT EXISTS idx_dashboard_notifications_trainer ON dashboard_notifications(trainer_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_notifications_read ON dashboard_notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_dashboard_tokens_trainer ON dashboard_tokens(trainer_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_tokens_token ON dashboard_tokens(token);

-- Calendar indexes
CREATE INDEX IF NOT EXISTS idx_calendar_sync_prefs_trainer ON calendar_sync_preferences(trainer_id);
CREATE INDEX IF NOT EXISTS idx_calendar_sync_status_trainer ON calendar_sync_status(trainer_id);
CREATE INDEX IF NOT EXISTS idx_calendar_sync_status_provider ON calendar_sync_status(provider);
CREATE INDEX IF NOT EXISTS idx_calendar_events_booking ON calendar_events(booking_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_external ON calendar_events(external_event_id);

-- Gamification indexes
CREATE INDEX IF NOT EXISTS idx_gamification_points_client ON gamification_points(client_id);
CREATE INDEX IF NOT EXISTS idx_gamification_points_trainer ON gamification_points(trainer_id);
CREATE INDEX IF NOT EXISTS idx_gamification_points_activity ON gamification_points(activity_type);

CREATE INDEX IF NOT EXISTS idx_achievements_client ON achievements(client_id);
CREATE INDEX IF NOT EXISTS idx_achievements_trainer ON achievements(trainer_id);
CREATE INDEX IF NOT EXISTS idx_achievements_type ON achievements(achievement_type);

CREATE INDEX IF NOT EXISTS idx_leaderboards_trainer ON leaderboards(trainer_id);
CREATE INDEX IF NOT EXISTS idx_leaderboards_type ON leaderboards(leaderboard_type);
CREATE INDEX IF NOT EXISTS idx_leaderboards_period ON leaderboards(period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_challenge_progress_client ON challenge_progress(client_id);
CREATE INDEX IF NOT EXISTS idx_challenge_progress_trainer ON challenge_progress(trainer_id);
CREATE INDEX IF NOT EXISTS idx_challenge_progress_status ON challenge_progress(status);
CREATE INDEX IF NOT EXISTS idx_challenge_progress_dates ON challenge_progress(start_date, end_date);

-- ============================================
-- FUNCTIONS AND TRIGGERS
-- ============================================

-- Function to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers to relevant tables
CREATE TRIGGER update_trainers_updated_at 
    BEFORE UPDATE ON trainers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clients_updated_at 
    BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bookings_updated_at 
    BEFORE UPDATE ON bookings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_habit_tracking_updated_at 
    BEFORE UPDATE ON habit_tracking
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_habits_updated_at 
    BEFORE UPDATE ON habits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_habit_goals_updated_at 
    BEFORE UPDATE ON habit_goals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_assessment_templates_updated_at 
    BEFORE UPDATE ON assessment_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fitness_assessments_updated_at 
    BEFORE UPDATE ON fitness_assessments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_assessments_updated_at 
    BEFORE UPDATE ON assessments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workouts_updated_at 
    BEFORE UPDATE ON workouts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversation_states_updated_at 
    BEFORE UPDATE ON conversation_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_registration_states_updated_at 
    BEFORE UPDATE ON registration_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_registration_sessions_updated_at 
    BEFORE UPDATE ON registration_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_flow_tokens_updated_at 
    BEFORE UPDATE ON flow_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_requests_updated_at 
    BEFORE UPDATE ON payment_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at 
    BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_client_payment_tokens_updated_at 
    BEFORE UPDATE ON client_payment_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscription_plans_updated_at 
    BEFORE UPDATE ON subscription_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trainer_subscriptions_updated_at 
    BEFORE UPDATE ON trainer_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dashboard_stats_updated_at 
    BEFORE UPDATE ON dashboard_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_sync_preferences_updated_at 
    BEFORE UPDATE ON calendar_sync_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_sync_status_updated_at 
    BEFORE UPDATE ON calendar_sync_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leaderboards_updated_at 
    BEFORE UPDATE ON leaderboards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_challenge_progress_updated_at 
    BEFORE UPDATE ON challenge_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to expire old registration sessions
CREATE OR REPLACE FUNCTION expire_old_registration_sessions()
RETURNS void AS $$
BEGIN
    UPDATE registration_sessions
    SET status = 'expired'
    WHERE status IN ('active', 'in_progress') 
    AND (expires_at < NOW() OR created_at < NOW() - INTERVAL '48 hours');
    
    UPDATE registration_states
    SET completed = TRUE
    WHERE completed = FALSE
    AND created_at < NOW() - INTERVAL '48 hours';
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup expired flow tokens
CREATE OR REPLACE FUNCTION cleanup_expired_flow_tokens()
RETURNS void AS $$
BEGIN
    UPDATE flow_tokens
    SET status = 'expired'
    WHERE status = 'active'
    AND created_at < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup expired token setup requests
CREATE OR REPLACE FUNCTION cleanup_expired_token_setup()
RETURNS void AS $$
BEGIN
    UPDATE token_setup_requests
    SET status = 'expired'
    WHERE status = 'pending'
    AND expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on all tables
ALTER TABLE trainers ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE habits ENABLE ROW LEVEL SECURITY;
ALTER TABLE habit_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE habit_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE workouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE fitness_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE registration_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE registration_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE registration_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE flow_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE flow_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_payment_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE token_setup_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE trainer_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_payment_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_sync_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_sync_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE gamification_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE achievements ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaderboards ENABLE ROW LEVEL SECURITY;
ALTER TABLE challenge_progress ENABLE ROW LEVEL SECURITY;

-- Note: RLS policies would be implemented based on your authentication system
-- For now, we'll create basic policies assuming phone number-based authentication

-- Basic RLS policies (adjust based on your auth system)
CREATE POLICY "Users can access their own data" ON trainers
    FOR ALL USING (whatsapp = current_setting('app.current_phone', true));

CREATE POLICY "Trainers can manage their clients" ON clients
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Clients can view their own data" ON clients
    FOR SELECT USING (whatsapp = current_setting('app.current_phone', true));

-- Similar policies would be created for other tables...

-- ============================================
-- INITIAL DATA
-- ============================================

-- Insert default subscription plans
INSERT INTO subscription_plans (plan_code, name, description, price_monthly, price_annual, features) VALUES
('free', 'Free Plan', 'Basic features for new trainers', 0.00, 0.00, '{"max_clients": 3, "features": ["basic_scheduling", "whatsapp_bot"]}'),
('professional', 'Professional Plan', 'Full features for growing trainers', 49.00, 490.00, '{"max_clients": null, "features": ["all_features", "priority_support", "analytics"]}')
ON CONFLICT (plan_code) DO NOTHING;

-- ============================================
-- SCHEDULED JOBS (requires pg_cron extension)
-- ============================================

-- Schedule cleanup jobs
SELECT cron.schedule('expire-registration-sessions', '*/5 * * * *', 'SELECT expire_old_registration_sessions();');
SELECT cron.schedule('cleanup-flow-tokens', '0 * * * *', 'SELECT cleanup_expired_flow_tokens();');
SELECT cron.schedule('cleanup-token-setup', '0 * * * *', 'SELECT cleanup_expired_token_setup();');

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================

COMMENT ON DATABASE postgres IS 'Refiloe WhatsApp AI Assistant Database - Complete schema with all backend interactions';

-- Table comments
COMMENT ON TABLE trainers IS 'Personal trainers using the WhatsApp AI Assistant';
COMMENT ON TABLE clients IS 'Clients of trainers using the system';
COMMENT ON TABLE bookings IS 'Scheduled training sessions between trainers and clients';
COMMENT ON TABLE habits IS 'Habit tracking table for test compatibility';
COMMENT ON TABLE habit_tracking IS 'Daily habit and metric tracking for clients';
COMMENT ON TABLE habit_goals IS 'Habit goals set by clients';
COMMENT ON TABLE workouts IS 'Workout plans and exercises for clients';
COMMENT ON TABLE messages IS 'WhatsApp messages processed by the AI assistant';
COMMENT ON TABLE message_history IS 'Complete history of all WhatsApp messages';
COMMENT ON TABLE conversation_states IS 'Current conversation state for each user';
COMMENT ON TABLE assessments IS 'Client assessments and progress tracking (compatibility)';
COMMENT ON TABLE fitness_assessments IS 'Comprehensive fitness assessments';
COMMENT ON TABLE assessment_templates IS 'Templates for fitness assessments';
COMMENT ON TABLE registration_states IS 'Registration flow state management';
COMMENT ON TABLE registration_sessions IS 'Registration sessions (compatibility)';
COMMENT ON TABLE registration_analytics IS 'Analytics for registration optimization';
COMMENT ON TABLE registration_attempts IS 'Tracking of registration attempts';
COMMENT ON TABLE flow_tokens IS 'WhatsApp Flow tokens for interactive forms';
COMMENT ON TABLE flow_responses IS 'Responses from WhatsApp Flows';
COMMENT ON TABLE payment_requests IS 'Payment requests from trainers to clients';
COMMENT ON TABLE payments IS 'Completed payments';
COMMENT ON TABLE client_payment_tokens IS 'Saved payment methods for clients';
COMMENT ON TABLE token_setup_requests IS 'Payment method setup requests';
COMMENT ON TABLE payfast_webhooks IS 'PayFast webhook notifications';
COMMENT ON TABLE subscription_plans IS 'Available subscription plans';
COMMENT ON TABLE trainer_subscriptions IS 'Trainer subscription records';
COMMENT ON TABLE subscription_payment_history IS 'Subscription payment history';
COMMENT ON TABLE analytics_events IS 'User behavior analytics events';
COMMENT ON TABLE activity_logs IS 'User activity logs';
COMMENT ON TABLE dashboard_stats IS 'Dashboard statistics cache';
COMMENT ON TABLE dashboard_notifications IS 'Dashboard notifications';
COMMENT ON TABLE dashboard_tokens IS 'Dashboard access tokens';
COMMENT ON TABLE calendar_sync_preferences IS 'Calendar synchronization preferences';
COMMENT ON TABLE calendar_sync_status IS 'Calendar synchronization status';
COMMENT ON TABLE calendar_events IS 'Calendar event mappings';
COMMENT ON TABLE gamification_points IS 'Gamification points earned by clients';
COMMENT ON TABLE achievements IS 'Achievements unlocked by clients';
COMMENT ON TABLE leaderboards IS 'Leaderboard rankings';
COMMENT ON TABLE challenge_progress IS 'Progress tracking for challenges';
COMMENT ON TABLE trainers_archive IS 'Archived trainer records';
COMMENT ON TABLE clients_archive IS 'Archived client records';

-- ============================================
-- END OF SCHEMA
-- ============================================