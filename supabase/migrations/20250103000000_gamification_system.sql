-- Migration: Add gamification system tables
-- Description: Creates tables for gamification features including profiles, challenges, progress tracking, and points ledger
-- Date: 2025-01-03
-- Timezone: Africa/Johannesburg (SAST)

-- ============================================
-- 1. GAMIFICATION PROFILES
-- ============================================
CREATE TABLE IF NOT EXISTS gamification_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    nickname VARCHAR(100),
    points_total INTEGER DEFAULT 0,
    is_public BOOLEAN DEFAULT FALSE,
    opted_in_global BOOLEAN DEFAULT FALSE,
    opted_in_trainer BOOLEAN DEFAULT TRUE,
    notification_preferences JSONB DEFAULT '{
        "achievements": true,
        "challenges": true,
        "leaderboard": true,
        "points": true
    }'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure either trainer_id or client_id is set, but not both
    CONSTRAINT check_user_type CHECK (
        (trainer_id IS NOT NULL AND client_id IS NULL) OR 
        (trainer_id IS NULL AND client_id IS NOT NULL)
    ),
    
    -- Ensure unique profile per user
    CONSTRAINT unique_trainer_profile UNIQUE (trainer_id),
    CONSTRAINT unique_client_profile UNIQUE (client_id)
);

-- ============================================
-- 2. CHALLENGES
-- ============================================
CREATE TABLE IF NOT EXISTS challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by UUID REFERENCES trainers(id) ON DELETE SET NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL, -- 'individual', 'group', 'trainer_wide', 'global'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    target_value DECIMAL(10,2),
    points_reward INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    max_participants INTEGER,
    challenge_rules JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure end date is after start date
    CONSTRAINT check_dates CHECK (end_date > start_date),
    -- Ensure positive points reward
    CONSTRAINT check_points_positive CHECK (points_reward > 0),
    -- Ensure positive max participants if set
    CONSTRAINT check_max_participants CHECK (max_participants IS NULL OR max_participants > 0)
);

-- ============================================
-- 3. CHALLENGE PARTICIPANTS
-- ============================================
CREATE TABLE IF NOT EXISTS challenge_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    challenge_id UUID NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL, -- 'trainer' or 'client'
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'completed', 'withdrawn', 'disqualified'
    final_position INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure unique participation per user per challenge
    CONSTRAINT unique_challenge_participant UNIQUE (challenge_id, user_id, user_type),
    -- Validate user_type
    CONSTRAINT check_user_type_valid CHECK (user_type IN ('trainer', 'client')),
    -- Validate status
    CONSTRAINT check_status_valid CHECK (status IN ('active', 'completed', 'withdrawn', 'disqualified'))
);

-- ============================================
-- 4. CHALLENGE PROGRESS
-- ============================================
CREATE TABLE IF NOT EXISTS challenge_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES challenge_participants(id) ON DELETE CASCADE,
    challenge_id UUID NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    value_achieved DECIMAL(10,2) NOT NULL DEFAULT 0,
    points_earned INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure unique progress entry per participant per day
    CONSTRAINT unique_daily_progress UNIQUE (participant_id, challenge_id, date),
    -- Ensure non-negative values
    CONSTRAINT check_value_non_negative CHECK (value_achieved >= 0),
    CONSTRAINT check_points_non_negative CHECK (points_earned >= 0)
);

-- ============================================
-- 5. POINTS LEDGER
-- ============================================
CREATE TABLE IF NOT EXISTS points_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL, -- 'trainer' or 'client'
    points INTEGER NOT NULL,
    reason VARCHAR(500) NOT NULL,
    challenge_id UUID REFERENCES challenges(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Validate user_type
    CONSTRAINT check_ledger_user_type CHECK (user_type IN ('trainer', 'client'))
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Gamification profiles indexes
CREATE INDEX idx_gamification_profiles_trainer_id ON gamification_profiles(trainer_id) WHERE trainer_id IS NOT NULL;
CREATE INDEX idx_gamification_profiles_client_id ON gamification_profiles(client_id) WHERE client_id IS NOT NULL;
CREATE INDEX idx_gamification_profiles_points ON gamification_profiles(points_total) WHERE is_public = TRUE;
CREATE INDEX idx_gamification_profiles_public ON gamification_profiles(is_public);

-- Challenges indexes
CREATE INDEX idx_challenges_created_by ON challenges(created_by);
CREATE INDEX idx_challenges_active ON challenges(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_challenges_dates ON challenges(start_date, end_date);
CREATE INDEX idx_challenges_type ON challenges(type);

-- Challenge participants indexes
CREATE INDEX idx_challenge_participants_challenge ON challenge_participants(challenge_id);
CREATE INDEX idx_challenge_participants_user ON challenge_participants(user_id, user_type);
CREATE INDEX idx_challenge_participants_status ON challenge_participants(status);
CREATE INDEX idx_challenge_participants_position ON challenge_participants(final_position) WHERE final_position IS NOT NULL;

-- Challenge progress indexes
CREATE INDEX idx_challenge_progress_participant ON challenge_progress(participant_id);
CREATE INDEX idx_challenge_progress_challenge ON challenge_progress(challenge_id);
CREATE INDEX idx_challenge_progress_date ON challenge_progress(date);
CREATE INDEX idx_challenge_progress_participant_date ON challenge_progress(participant_id, date);

-- Points ledger indexes
CREATE INDEX idx_points_ledger_user ON points_ledger(user_id, user_type);
CREATE INDEX idx_points_ledger_challenge ON points_ledger(challenge_id) WHERE challenge_id IS NOT NULL;
CREATE INDEX idx_points_ledger_created ON points_ledger(created_at);
CREATE INDEX idx_points_ledger_user_created ON points_ledger(user_id, created_at DESC);

-- ============================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
CREATE TRIGGER update_gamification_profiles_updated_at 
    BEFORE UPDATE ON gamification_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_challenges_updated_at 
    BEFORE UPDATE ON challenges 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_challenge_participants_updated_at 
    BEFORE UPDATE ON challenge_participants 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_challenge_progress_updated_at 
    BEFORE UPDATE ON challenge_progress 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- TRIGGER TO UPDATE POINTS TOTAL
-- ============================================

-- Function to update points_total in gamification_profiles
CREATE OR REPLACE FUNCTION update_points_total()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the points_total in gamification_profiles
    IF NEW.user_type = 'trainer' THEN
        UPDATE gamification_profiles 
        SET points_total = points_total + NEW.points
        WHERE trainer_id = NEW.user_id;
    ELSIF NEW.user_type = 'client' THEN
        UPDATE gamification_profiles 
        SET points_total = points_total + NEW.points
        WHERE client_id = NEW.user_id;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger for points ledger
CREATE TRIGGER update_points_total_trigger 
    AFTER INSERT ON points_ledger 
    FOR EACH ROW EXECUTE FUNCTION update_points_total();

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on all tables
ALTER TABLE gamification_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE challenges ENABLE ROW LEVEL SECURITY;
ALTER TABLE challenge_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE challenge_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE points_ledger ENABLE ROW LEVEL SECURITY;

-- Note: Actual RLS policies would be created based on your authentication system
-- Example policies commented below:

-- -- Gamification profiles: Users can view their own profile and public profiles
-- CREATE POLICY "Users can view own gamification profile" ON gamification_profiles
--     FOR SELECT USING (
--         auth.uid() = trainer_id::text OR 
--         auth.uid() = client_id::text OR 
--         is_public = TRUE
--     );

-- -- Challenges: Anyone can view active challenges
-- CREATE POLICY "View active challenges" ON challenges
--     FOR SELECT USING (is_active = TRUE);

-- ============================================
-- SAMPLE DATA FOR TESTING (OPTIONAL)
-- ============================================

-- Uncomment to insert sample challenge types
-- INSERT INTO challenges (name, description, type, start_date, end_date, target_value, points_reward, challenge_rules)
-- VALUES 
--     ('30-Day Workout Streak', 'Complete a workout every day for 30 days', 'individual', 
--      CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days', 30, 500, 
--      '{"min_duration": 30, "rest_days_allowed": 0}'::jsonb),
--     ('Steps Challenge', 'Walk 10,000 steps daily', 'group', 
--      CURRENT_DATE, CURRENT_DATE + INTERVAL '7 days', 70000, 200,
--      '{"daily_target": 10000, "measurement": "steps"}'::jsonb);

-- ============================================
-- ROLLBACK SECTION
-- ============================================

-- To rollback this migration, run the following commands:
-- 
-- -- Drop triggers first
-- DROP TRIGGER IF EXISTS update_points_total_trigger ON points_ledger;
-- DROP TRIGGER IF EXISTS update_challenge_progress_updated_at ON challenge_progress;
-- DROP TRIGGER IF EXISTS update_challenge_participants_updated_at ON challenge_participants;
-- DROP TRIGGER IF EXISTS update_challenges_updated_at ON challenges;
-- DROP TRIGGER IF EXISTS update_gamification_profiles_updated_at ON gamification_profiles;
-- 
-- -- Drop functions
-- DROP FUNCTION IF EXISTS update_points_total();
-- DROP FUNCTION IF EXISTS update_updated_at_column();
-- 
-- -- Drop tables in reverse order (due to foreign key constraints)
-- DROP TABLE IF EXISTS points_ledger CASCADE;
-- DROP TABLE IF EXISTS challenge_progress CASCADE;
-- DROP TABLE IF EXISTS challenge_participants CASCADE;
-- DROP TABLE IF EXISTS challenges CASCADE;
-- DROP TABLE IF EXISTS gamification_profiles CASCADE;
-- 
-- -- Note: CASCADE will also drop all associated indexes and constraints

-- ============================================
-- MIGRATION COMPLETED
-- ============================================