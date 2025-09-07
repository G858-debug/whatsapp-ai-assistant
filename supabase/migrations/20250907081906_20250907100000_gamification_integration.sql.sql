-- Add gamification profile columns if missing
ALTER TABLE gamification_profiles 
ADD COLUMN IF NOT EXISTS points_this_week INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS points_this_month INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_points_earned TIMESTAMPTZ;

-- Create point logs table for tracking
CREATE TABLE IF NOT EXISTS point_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL,
    action VARCHAR(50) NOT NULL,
    points INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    INDEX idx_point_logs_user (user_id, user_type),
    INDEX idx_point_logs_date (created_at)
);

-- Create user badges table
CREATE TABLE IF NOT EXISTS user_badges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL,
    badge_id VARCHAR(50) NOT NULL,
    earned_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE KEY unique_user_badge (user_id, user_type, badge_id),
    INDEX idx_user_badges (user_id, user_type)
);

-- Create badges definition table
CREATE TABLE IF NOT EXISTS badges (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_emoji VARCHAR(10),
    criteria_type VARCHAR(50),
    criteria_threshold INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default badges
INSERT INTO badges (id, name, description, icon_emoji, criteria_type, criteria_threshold) VALUES
('improver', 'Improver', 'Achieved 10% improvement in assessments', '📈', 'assessment_improvement', 10),
('consistency_king', 'Consistency King', 'Logged habits for 30 days straight', '👑', 'habit_streak', 30),
('workout_warrior', 'Workout Warrior', 'Completed 20 workouts', '💪', 'workouts_completed', 20),
('habit_hero', 'Habit Hero', 'Logged 100 habits', '🦸', 'habits_logged', 100)
ON CONFLICT (id) DO NOTHING;