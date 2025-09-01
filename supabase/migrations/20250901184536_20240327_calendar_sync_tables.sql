-- Calendar sync preferences
CREATE TABLE calendar_sync_preferences (
    trainer_id UUID REFERENCES trainers(id) PRIMARY KEY,
    google_calendar_enabled BOOLEAN DEFAULT FALSE,
    apple_calendar_enabled BOOLEAN DEFAULT FALSE,
    email_calendar_enabled BOOLEAN DEFAULT FALSE,
    sync_frequency VARCHAR(20) DEFAULT 'realtime',
    calendar_view_default VARCHAR(20) DEFAULT 'month',
    show_client_names BOOLEAN DEFAULT TRUE,
    session_colors JSONB DEFAULT '{}',
    timezone_display VARCHAR(100) DEFAULT 'Africa/Johannesburg',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Calendar sync status
CREATE TABLE calendar_sync_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trainer_id UUID REFERENCES trainers(id),
    provider VARCHAR(50) NOT NULL,
    last_sync TIMESTAMPTZ,
    sync_status VARCHAR(20),
    events_synced INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trainer_id, provider)
);

-- Calendar events mapping
CREATE TABLE calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID REFERENCES bookings(id),
    external_event_id VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(booking_id, provider)
);

-- Add calendar fields to bookings table
ALTER TABLE bookings 
ADD COLUMN google_event_id VARCHAR(255),
ADD COLUMN apple_event_id VARCHAR(255),
ADD COLUMN session_type VARCHAR(50) DEFAULT 'one_on_one',
ADD COLUMN color_hex VARCHAR(7);

-- Create indexes
CREATE INDEX idx_calendar_sync_status_trainer ON calendar_sync_status(trainer_id);
CREATE INDEX idx_calendar_events_booking ON calendar_events(booking_id);
CREATE INDEX idx_bookings_session_type ON bookings(session_type);