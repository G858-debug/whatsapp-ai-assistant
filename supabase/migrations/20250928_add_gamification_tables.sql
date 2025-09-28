-- Additional Migration: Add Gamification Tables
-- Run this after the main migration to add the missing gamification tables

-- Drop existing tables if they exist (for clean migration)
DROP TABLE IF EXISTS challenge_progress CASCADE;
DROP TABLE IF EXISTS challenge_participants CASCADE;
DROP TABLE IF EXISTS challenges CASCADE;
DROP TABLE IF EXISTS gamification_profiles CASCADE;

-- ============================================
-- 1. GAMIFICATION PROFILES
-- ============================================
CREATE TABLE gamification_profiles (
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
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
CREATE TABLE challenges (
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
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
CREATE TABLE challenge_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    challenge_id UUID NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL, -- 'trainer' or 'client'
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'completed', 'withdrawn', 'disqualified'
    final_position INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
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
CREATE TABLE challenge_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID NOT NULL REFERENCES challenge_participants(id) ON DELETE CASCADE,
    challenge_id UUID NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    value_achieved DECIMAL(10,2) NOT NULL DEFAULT 0,
    points_earned INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique progress entry per participant per day
    CONSTRAINT unique_progress_per_day UNIQUE (participant_id, date)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Gamification profiles indexes
CREATE INDEX IF NOT EXISTS idx_gamification_profiles_trainer ON gamification_profiles(trainer_id);
CREATE INDEX IF NOT EXISTS idx_gamification_profiles_client ON gamification_profiles(client_id);
CREATE INDEX IF NOT EXISTS idx_gamification_profiles_points ON gamification_profiles(points_total);

-- Challenges indexes
CREATE INDEX IF NOT EXISTS idx_challenges_created_by ON challenges(created_by);
CREATE INDEX IF NOT EXISTS idx_challenges_dates ON challenges(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_challenges_active ON challenges(is_active);

-- Challenge participants indexes
CREATE INDEX IF NOT EXISTS idx_challenge_participants_challenge ON challenge_participants(challenge_id);
CREATE INDEX IF NOT EXISTS idx_challenge_participants_user ON challenge_participants(user_id, user_type);
CREATE INDEX IF NOT EXISTS idx_challenge_participants_status ON challenge_participants(status);

-- Challenge progress indexes
CREATE INDEX IF NOT EXISTS idx_challenge_progress_participant ON challenge_progress(participant_id);
CREATE INDEX IF NOT EXISTS idx_challenge_progress_challenge ON challenge_progress(challenge_id);
CREATE INDEX IF NOT EXISTS idx_challenge_progress_date ON challenge_progress(date);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on all tables
ALTER TABLE gamification_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE challenges ENABLE ROW LEVEL SECURITY;
ALTER TABLE challenge_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE challenge_progress ENABLE ROW LEVEL SECURITY;

-- Gamification profiles policies
CREATE POLICY "Users can manage their own profiles" ON gamification_profiles
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        ) OR
        client_id IN (
            SELECT id FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- Challenges policies
CREATE POLICY "Trainers can manage their challenges" ON challenges
    FOR ALL USING (
        created_by IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- Challenge participants policies
CREATE POLICY "Users can manage their challenge participation" ON challenge_participants
    FOR ALL USING (
        user_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        ) OR
        user_id IN (
            SELECT id FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- Challenge progress policies
CREATE POLICY "Users can manage their challenge progress" ON challenge_progress
    FOR ALL USING (
        participant_id IN (
            SELECT id FROM challenge_participants 
            WHERE user_id IN (
                SELECT id FROM trainers 
                WHERE whatsapp = current_setting('app.current_phone', true)
            ) OR
            user_id IN (
                SELECT id FROM clients 
                WHERE whatsapp = current_setting('app.current_phone', true)
            )
        )
    );

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================
COMMENT ON TABLE gamification_profiles IS 'User profiles for gamification features';
COMMENT ON TABLE challenges IS 'Challenges and competitions for users';
COMMENT ON TABLE challenge_participants IS 'Users participating in challenges';
COMMENT ON TABLE challenge_progress IS 'Daily progress tracking for challenge participants';
