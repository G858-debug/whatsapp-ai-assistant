-- Migration: Add Missing Core Tables
-- Description: Creates tables that are referenced in the codebase but missing from current schema
-- Date: 2025-01-15

-- ============================================
-- 1. REGISTRATION ANALYTICS TABLE
-- ============================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_registration_analytics_phone ON registration_analytics(phone_number);
CREATE INDEX IF NOT EXISTS idx_registration_analytics_event ON registration_analytics(event_type);
CREATE INDEX IF NOT EXISTS idx_registration_analytics_timestamp ON registration_analytics(timestamp);

-- ============================================
-- 2. REGISTRATION ATTEMPTS TABLE
-- ============================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_registration_attempts_phone ON registration_attempts(phone);
CREATE INDEX IF NOT EXISTS idx_registration_attempts_user ON registration_attempts(existing_user_id);
CREATE INDEX IF NOT EXISTS idx_registration_attempts_created ON registration_attempts(created_at);

-- ============================================
-- 3. HABIT GOALS TABLE
-- ============================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_habit_goals_client ON habit_goals(client_id);
CREATE INDEX IF NOT EXISTS idx_habit_goals_type ON habit_goals(habit_type);
CREATE INDEX IF NOT EXISTS idx_habit_goals_active ON habit_goals(is_active);

-- ============================================
-- 4. ANALYTICS EVENTS TABLE
-- ============================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_analytics_events_user ON analytics_events(user_id, user_type);
CREATE INDEX IF NOT EXISTS idx_analytics_events_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_events_timestamp ON analytics_events(timestamp);

-- ============================================
-- 5. ACTIVITY LOGS TABLE
-- ============================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id, user_type);
CREATE INDEX IF NOT EXISTS idx_activity_logs_type ON activity_logs(activity_type);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON activity_logs(created_at);

-- ============================================
-- 6. DASHBOARD STATS TABLE
-- ============================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dashboard_stats_trainer ON dashboard_stats(trainer_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_stats_date ON dashboard_stats(stat_date);

-- ============================================
-- 7. DASHBOARD NOTIFICATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS dashboard_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    notification_type VARCHAR(50),
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dashboard_notifications_trainer ON dashboard_notifications(trainer_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_notifications_read ON dashboard_notifications(is_read);

-- ============================================
-- 8. DASHBOARD TOKENS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS dashboard_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dashboard_tokens_trainer ON dashboard_tokens(trainer_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_tokens_token ON dashboard_tokens(token);

-- ============================================
-- 9. TRIGGERS FOR UPDATED_AT
-- ============================================

-- Function to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_habit_goals_updated_at 
    BEFORE UPDATE ON habit_goals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dashboard_stats_updated_at 
    BEFORE UPDATE ON dashboard_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 10. COMMENTS FOR DOCUMENTATION
-- ============================================
COMMENT ON TABLE registration_analytics IS 'Analytics for registration optimization';
COMMENT ON TABLE registration_attempts IS 'Tracking of registration attempts';
COMMENT ON TABLE habit_goals IS 'Habit goals set by clients';
COMMENT ON TABLE analytics_events IS 'User behavior analytics events';
COMMENT ON TABLE activity_logs IS 'User activity logs';
COMMENT ON TABLE dashboard_stats IS 'Dashboard statistics cache';
COMMENT ON TABLE dashboard_notifications IS 'Dashboard notifications';
COMMENT ON TABLE dashboard_tokens IS 'Dashboard access tokens';

-- ============================================
-- 11. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on new tables
ALTER TABLE registration_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE registration_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE habit_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_tokens ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (adjust based on your auth system)
CREATE POLICY "Users can view their registration analytics" ON registration_analytics
    FOR SELECT USING (phone_number = current_setting('app.current_phone', true));

CREATE POLICY "Users can view their registration attempts" ON registration_attempts
    FOR SELECT USING (phone = current_setting('app.current_phone', true));

CREATE POLICY "Clients can manage their habit goals" ON habit_goals
    FOR ALL USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Trainers can view client habit goals" ON habit_goals
    FOR SELECT USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE trainer_id IN (
                SELECT id FROM trainers 
                WHERE whatsapp = current_setting('app.current_phone', true)
            )
        )
    );

CREATE POLICY "Users can view their analytics events" ON analytics_events
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can view their activity logs" ON activity_logs
    FOR SELECT USING (user_id::text = current_setting('app.current_user_id', true));

CREATE POLICY "Trainers can view their dashboard stats" ON dashboard_stats
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Trainers can view their dashboard notifications" ON dashboard_notifications
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Trainers can manage their dashboard tokens" ON dashboard_tokens
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );