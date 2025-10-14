-- Migration: Add Calendar and Gamification Tables
-- Description: Creates calendar sync and gamification tables referenced in the codebase
-- Date: 2025-01-15

-- ============================================
-- 1. CALENDAR SYNC PREFERENCES TABLE
-- ============================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_calendar_sync_prefs_trainer ON calendar_sync_preferences(trainer_id);

-- ============================================
-- 2. CALENDAR SYNC STATUS TABLE
-- ============================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_calendar_sync_status_trainer ON calendar_sync_status(trainer_id);
CREATE INDEX IF NOT EXISTS idx_calendar_sync_status_provider ON calendar_sync_status(provider);

-- ============================================
-- 3. CALENDAR EVENTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    external_event_id VARCHAR(255) NOT NULL,
    provider VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_calendar_events_booking ON calendar_events(booking_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_external ON calendar_events(external_event_id);

-- ============================================
-- 4. GAMIFICATION POINTS TABLE
-- ============================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_gamification_points_client ON gamification_points(client_id);
CREATE INDEX IF NOT EXISTS idx_gamification_points_trainer ON gamification_points(trainer_id);
CREATE INDEX IF NOT EXISTS idx_gamification_points_activity ON gamification_points(activity_type);

-- ============================================
-- 5. ACHIEVEMENTS TABLE
-- ============================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_achievements_client ON achievements(client_id);
CREATE INDEX IF NOT EXISTS idx_achievements_trainer ON achievements(trainer_id);
CREATE INDEX IF NOT EXISTS idx_achievements_type ON achievements(achievement_type);

-- ============================================
-- 6. LEADERBOARDS TABLE
-- ============================================
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_leaderboards_trainer ON leaderboards(trainer_id);
CREATE INDEX IF NOT EXISTS idx_leaderboards_type ON leaderboards(leaderboard_type);
CREATE INDEX IF NOT EXISTS idx_leaderboards_period ON leaderboards(period_start, period_end);

-- ============================================
-- 7. ARCHIVE TABLES
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
-- 8. TRIGGERS FOR UPDATED_AT
-- ============================================

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_calendar_sync_preferences_updated_at 
    BEFORE UPDATE ON calendar_sync_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_sync_status_updated_at 
    BEFORE UPDATE ON calendar_sync_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leaderboards_updated_at 
    BEFORE UPDATE ON leaderboards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 9. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on new tables
ALTER TABLE calendar_sync_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_sync_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE gamification_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE achievements ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaderboards ENABLE ROW LEVEL SECURITY;

-- Calendar sync policies
CREATE POLICY "Trainers can manage their calendar sync preferences" ON calendar_sync_preferences
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Trainers can view their calendar sync status" ON calendar_sync_status
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Trainers can view their calendar events" ON calendar_events
    FOR SELECT USING (
        booking_id IN (
            SELECT id FROM bookings 
            WHERE trainer_id IN (
                SELECT id FROM trainers 
                WHERE whatsapp = current_setting('app.current_phone', true)
            )
        )
    );

-- Gamification policies
CREATE POLICY "Clients can view their gamification points" ON gamification_points
    FOR SELECT USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Trainers can view client gamification points" ON gamification_points
    FOR SELECT USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Clients can view their achievements" ON achievements
    FOR SELECT USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Trainers can view client achievements" ON achievements
    FOR SELECT USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Trainers can manage their leaderboards" ON leaderboards
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- ============================================
-- 10. COMMENTS FOR DOCUMENTATION
-- ============================================
COMMENT ON TABLE calendar_sync_preferences IS 'Calendar synchronization preferences for trainers';
COMMENT ON TABLE calendar_sync_status IS 'Calendar synchronization status tracking';
COMMENT ON TABLE calendar_events IS 'Mapping between bookings and external calendar events';
COMMENT ON TABLE gamification_points IS 'Points earned by clients for various activities';
COMMENT ON TABLE achievements IS 'Achievements unlocked by clients';
COMMENT ON TABLE leaderboards IS 'Leaderboard rankings for clients';
COMMENT ON TABLE trainers_archive IS 'Archived trainer records for data retention';
COMMENT ON TABLE clients_archive IS 'Archived client records for data retention';

COMMENT ON COLUMN calendar_sync_preferences.sync_frequency IS 'How often to sync calendar events';
COMMENT ON COLUMN calendar_sync_preferences.event_title_template IS 'Template for calendar event titles';
COMMENT ON COLUMN calendar_sync_status.provider IS 'Calendar provider (google, outlook, etc.)';
COMMENT ON COLUMN calendar_sync_status.sync_status IS 'Status of last sync attempt';
COMMENT ON COLUMN calendar_events.external_event_id IS 'ID of event in external calendar system';
COMMENT ON COLUMN gamification_points.reason IS 'Reason points were awarded';
COMMENT ON COLUMN gamification_points.activity_type IS 'Type of activity that earned points';
COMMENT ON COLUMN achievements.achievement_type IS 'Category of achievement';
COMMENT ON COLUMN leaderboards.rankings IS 'JSON array of client rankings';
COMMENT ON COLUMN trainers_archive.archive_reason IS 'Reason for archiving the trainer record';
COMMENT ON COLUMN clients_archive.archive_reason IS 'Reason for archiving the client record';