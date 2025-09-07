-- Create badges table
CREATE TABLE IF NOT EXISTS badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    icon_emoji VARCHAR(10) NOT NULL,
    criteria_type VARCHAR(50) NOT NULL,
    criteria_value INTEGER NOT NULL,
    points_value INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create user_badges table
CREATE TABLE IF NOT EXISTS user_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('client', 'trainer')),
    badge_id UUID NOT NULL REFERENCES badges(id),
    earned_at TIMESTAMP WITH TIME ZONE NOT NULL,
    challenge_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, badge_id)
);

-- Create user_points table
CREATE TABLE IF NOT EXISTS user_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id),
    trainer_id UUID REFERENCES trainers(id),
    total_points INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (client_id IS NOT NULL AND trainer_id IS NULL) OR
        (client_id IS NULL AND trainer_id IS NOT NULL)
    )
);

-- Create indexes
CREATE INDEX idx_user_badges_user ON user_badges(user_id, user_type);
CREATE INDEX idx_user_badges_badge ON user_badges(badge_id);
CREATE INDEX idx_user_points_client ON user_points(client_id);
CREATE INDEX idx_user_points_trainer ON user_points(trainer_id);

-- Insert default badges
INSERT INTO badges (name, description, icon_emoji, criteria_type, criteria_value, points_value) VALUES
('First Workout', 'Completed your first workout!', '🎯', 'first_workout', 1, 100),
('Workout Warrior', 'Maintained a 7-day workout streak', '🔥', 'workout_streak', 7, 500),
('Challenge Champion', 'Won 3 fitness challenges', '🏆', 'challenge_wins', 3, 750),
('Points Master', 'Earned 1000 total points', '⭐', 'points_milestone', 1000, 1000);