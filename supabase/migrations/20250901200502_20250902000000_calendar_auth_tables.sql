-- Add Google Calendar auth table
CREATE TABLE google_auth (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainer_id UUID REFERENCES trainers(id) ON DELETE CASCADE,
    credentials JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trainer_id)
);

-- Add sync monitoring table
CREATE TABLE sync_monitoring (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainer_id UUID REFERENCES trainers(id),
    sync_type VARCHAR(50),
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    duration INTERVAL,
    events_synced INTEGER,
    errors INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_google_auth_trainer ON google_auth(trainer_id);
CREATE INDEX idx_sync_monitoring_trainer ON sync_monitoring(trainer_id);
CREATE INDEX idx_sync_monitoring_type ON sync_monitoring(sync_type);