-- Registration sessions table for managing registration flow
CREATE TABLE IF NOT EXISTS registration_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone VARCHAR(20) NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'expired', 'cancelled')),
    step VARCHAR(50) NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_registration_sessions_phone ON registration_sessions(phone);
CREATE INDEX idx_registration_sessions_status ON registration_sessions(status);
CREATE INDEX idx_registration_sessions_updated ON registration_sessions(updated_at);

-- Cleanup old sessions automatically (optional trigger)
CREATE OR REPLACE FUNCTION cleanup_expired_registration_sessions()
RETURNS void AS $$
BEGIN
    UPDATE registration_sessions 
    SET status = 'expired'
    WHERE status = 'active' 
    AND updated_at < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup (if using pg_cron extension)
-- SELECT cron.schedule('cleanup-registration-sessions', '0 * * * *', 'SELECT cleanup_expired_registration_sessions();');