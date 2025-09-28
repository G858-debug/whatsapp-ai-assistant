-- Migration: Add Flow Support Tables
-- Description: Creates tables for WhatsApp Flows tracking and management
-- Date: 2025-09-28
-- Timezone: Africa/Johannesburg (SAST)

-- ============================================
-- 1. FLOW TOKENS TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS flow_tokens CASCADE;

CREATE TABLE flow_tokens (
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

-- ============================================
-- 2. FLOW RESPONSES TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS flow_responses CASCADE;

CREATE TABLE flow_responses (
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
-- 3. UPDATE TRAINERS TABLE FOR FLOW SUPPORT
-- ============================================
-- Add flow-related columns to trainers table
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS flow_token VARCHAR(255);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS onboarding_method VARCHAR(20) DEFAULT 'chat' CHECK (onboarding_method IN ('chat', 'flow'));
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS specialization VARCHAR(100);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS experience_years VARCHAR(20);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS available_days JSONB DEFAULT '[]'::jsonb;
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS preferred_time_slots VARCHAR(50);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS notification_preferences JSONB DEFAULT '[]'::jsonb;
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE;
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS marketing_consent BOOLEAN DEFAULT FALSE;

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Flow tokens indexes
CREATE INDEX IF NOT EXISTS idx_flow_tokens_phone ON flow_tokens(phone_number);
CREATE INDEX IF NOT EXISTS idx_flow_tokens_token ON flow_tokens(flow_token);
CREATE INDEX IF NOT EXISTS idx_flow_tokens_type ON flow_tokens(flow_type);
CREATE INDEX IF NOT EXISTS idx_flow_tokens_status ON flow_tokens(status);
CREATE INDEX IF NOT EXISTS idx_flow_tokens_created ON flow_tokens(created_at);

-- Flow responses indexes
CREATE INDEX IF NOT EXISTS idx_flow_responses_token ON flow_responses(flow_token);
CREATE INDEX IF NOT EXISTS idx_flow_responses_phone ON flow_responses(phone_number);
CREATE INDEX IF NOT EXISTS idx_flow_responses_type ON flow_responses(flow_type);
CREATE INDEX IF NOT EXISTS idx_flow_responses_completed ON flow_responses(completed);
CREATE INDEX IF NOT EXISTS idx_flow_responses_processed ON flow_responses(processed);

-- Trainers flow indexes
CREATE INDEX IF NOT EXISTS idx_trainers_flow_token ON trainers(flow_token);
CREATE INDEX IF NOT EXISTS idx_trainers_onboarding_method ON trainers(onboarding_method);
CREATE INDEX IF NOT EXISTS idx_trainers_city ON trainers(city);
CREATE INDEX IF NOT EXISTS idx_trainers_specialization ON trainers(specialization);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can manage their flow tokens" ON flow_tokens;
DROP POLICY IF EXISTS "Users can view their flow responses" ON flow_responses;
DROP POLICY IF EXISTS "Users can insert their flow responses" ON flow_responses;

ALTER TABLE flow_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE flow_responses ENABLE ROW LEVEL SECURITY;

-- Flow tokens policies
CREATE POLICY "Users can manage their flow tokens" ON flow_tokens
    FOR ALL USING (phone_number = current_setting('app.current_phone', true));

-- Flow responses policies
CREATE POLICY "Users can view their flow responses" ON flow_responses
    FOR SELECT USING (phone_number = current_setting('app.current_phone', true));

CREATE POLICY "Users can insert their flow responses" ON flow_responses
    FOR INSERT WITH CHECK (phone_number = current_setting('app.current_phone', true));

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================
COMMENT ON TABLE flow_tokens IS 'Tracks active WhatsApp Flows for users';
COMMENT ON TABLE flow_responses IS 'Stores responses from completed WhatsApp Flows';

COMMENT ON COLUMN flow_tokens.flow_type IS 'Type of flow (trainer_onboarding, client_onboarding, etc.)';
COMMENT ON COLUMN flow_tokens.flow_data IS 'Additional flow configuration data';
COMMENT ON COLUMN flow_tokens.status IS 'Current status of the flow';
COMMENT ON COLUMN flow_responses.response_data IS 'Complete response data from the flow';
COMMENT ON COLUMN flow_responses.screen_id IS 'Last screen completed in the flow';
COMMENT ON COLUMN trainers.onboarding_method IS 'Method used for onboarding (chat or flow)';
COMMENT ON COLUMN trainers.flow_token IS 'Token used for flow-based onboarding';
