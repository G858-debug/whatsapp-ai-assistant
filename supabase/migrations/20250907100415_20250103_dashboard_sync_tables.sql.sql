-- Create notification queue table for digest management
CREATE TABLE IF NOT EXISTS notification_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    notification_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create dashboard updates table for real-time sync
CREATE TABLE IF NOT EXISTS dashboard_updates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    action VARCHAR(100) NOT NULL,
    data JSONB,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add dashboard URL preferences to gamification_profiles
ALTER TABLE gamification_profiles 
ADD COLUMN IF NOT EXISTS dashboard_access_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_dashboard_access TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS prefer_dashboard_for_complex BOOLEAN DEFAULT TRUE;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_notification_queue_user ON notification_queue(user_id, user_type);
CREATE INDEX IF NOT EXISTS idx_notification_queue_scheduled ON notification_queue(scheduled_for, sent);
CREATE INDEX IF NOT EXISTS idx_notification_queue_created ON notification_queue(created_at);
CREATE INDEX IF NOT EXISTS idx_dashboard_updates_user ON dashboard_updates(user_id, user_type);
CREATE INDEX IF NOT EXISTS idx_dashboard_updates_created ON dashboard_updates(created_at);
CREATE INDEX IF NOT EXISTS idx_dashboard_updates_processed ON dashboard_updates(processed);

-- Comment for rollback:
-- DROP TABLE IF EXISTS notification_queue;
-- DROP TABLE IF EXISTS dashboard_updates;
-- ALTER TABLE gamification_profiles 
-- DROP COLUMN IF EXISTS dashboard_access_count,
-- DROP COLUMN IF EXISTS last_dashboard_access,
-- DROP COLUMN IF EXISTS prefer_dashboard_for_complex;