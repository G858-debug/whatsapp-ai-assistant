-- Create leaderboards table
CREATE TABLE IF NOT EXISTS leaderboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'points', 'challenge', 'workout', 'habit'
    scope VARCHAR(50) NOT NULL, -- 'global', 'trainer-only', 'client-group'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create leaderboard_entries table
CREATE TABLE IF NOT EXISTS leaderboard_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    leaderboard_id UUID NOT NULL REFERENCES leaderboards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('client', 'trainer')),
    nickname VARCHAR(100),
    points INTEGER NOT NULL DEFAULT 0,
    rank INTEGER,
    previous_rank INTEGER,
    best_rank INTEGER,
    trend VARCHAR(10) CHECK (trend IN ('up', 'down', 'same')),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(leaderboard_id, user_id, user_type)
);

-- Create indexes for performance
CREATE INDEX idx_leaderboards_active ON leaderboards(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_leaderboards_scope ON leaderboards(scope);
CREATE INDEX idx_leaderboards_dates ON leaderboards(start_date, end_date);

CREATE INDEX idx_leaderboard_entries_leaderboard ON leaderboard_entries(leaderboard_id);
CREATE INDEX idx_leaderboard_entries_user ON leaderboard_entries(user_id, user_type);
CREATE INDEX idx_leaderboard_entries_rank ON leaderboard_entries(leaderboard_id, rank);
CREATE INDEX idx_leaderboard_entries_points ON leaderboard_entries(leaderboard_id, points DESC);

-- Insert sample leaderboards
INSERT INTO leaderboards (name, type, scope, start_date, end_date) VALUES
('Water Challenge Leaderboard', 'habit', 'global', CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days'),
('January Fitness Challenge', 'points', 'global', '2025-01-01', '2025-01-31'),
('Weekly Steps Challenge', 'habit', 'trainer-only', CURRENT_DATE, CURRENT_DATE + INTERVAL '7 days');