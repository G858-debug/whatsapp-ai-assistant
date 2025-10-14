-- Migration: Add Registration Sessions Compatibility Table
-- Description: Creates registration_sessions table for backward compatibility with existing code
-- Date: 2025-01-15

-- ============================================
-- 1. REGISTRATION SESSIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS registration_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    registration_type VARCHAR(20) NOT NULL CHECK (registration_type IN ('trainer', 'client', 'unknown')),
    step VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'in_progress', 'completed', 'expired', 'cancelled', 'abandoned', 'error')),
    data JSONB DEFAULT '{}'::jsonb,
    retry_count INTEGER DEFAULT 0,
    needs_retry BOOLEAN DEFAULT FALSE,
    last_error_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for registration sessions
CREATE INDEX IF NOT EXISTS idx_registration_sessions_phone ON registration_sessions(phone);
CREATE INDEX IF NOT EXISTS idx_registration_sessions_status ON registration_sessions(status);
CREATE INDEX IF NOT EXISTS idx_registration_sessions_expires ON registration_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_registration_sessions_needs_retry ON registration_sessions(needs_retry) WHERE needs_retry = TRUE;

-- ============================================
-- 2. FUNCTIONS FOR REGISTRATION MANAGEMENT
-- ============================================

-- Function to expire old registration sessions
CREATE OR REPLACE FUNCTION expire_old_registration_sessions()
RETURNS void AS $$
BEGIN
    UPDATE registration_sessions
    SET status = 'expired'
    WHERE status IN ('active', 'in_progress') 
    AND (expires_at < NOW() OR created_at < NOW() - INTERVAL '48 hours');
    
    UPDATE registration_states
    SET completed = TRUE
    WHERE completed = FALSE
    AND created_at < NOW() - INTERVAL '48 hours';
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup expired flow tokens
CREATE OR REPLACE FUNCTION cleanup_expired_flow_tokens()
RETURNS void AS $$
BEGIN
    UPDATE flow_tokens
    SET status = 'expired'
    WHERE status = 'active'
    AND created_at < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup expired token setup requests
CREATE OR REPLACE FUNCTION cleanup_expired_token_setup()
RETURNS void AS $$
BEGIN
    UPDATE token_setup_requests
    SET status = 'expired'
    WHERE status = 'pending'
    AND expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to increment retry count
CREATE OR REPLACE FUNCTION increment(x INTEGER, row_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN x + 1;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 3. TRIGGERS FOR UPDATED_AT
-- ============================================

-- Apply trigger to registration_sessions
CREATE TRIGGER update_registration_sessions_updated_at 
    BEFORE UPDATE ON registration_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 4. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on registration_sessions
ALTER TABLE registration_sessions ENABLE ROW LEVEL SECURITY;

-- Registration sessions - trainers can see their own
CREATE POLICY "Trainers can view own registration sessions"
    ON registration_sessions FOR SELECT
    USING (
        phone IN (
            SELECT whatsapp FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- Registration sessions - clients can see their own
CREATE POLICY "Clients can view own registration sessions"
    ON registration_sessions FOR SELECT
    USING (
        phone IN (
            SELECT whatsapp FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- ============================================
-- 5. SCHEDULED JOBS (requires pg_cron extension)
-- ============================================

-- Schedule cleanup jobs (only if pg_cron is available)
DO $$
BEGIN
    -- Check if pg_cron extension exists
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        -- Schedule cleanup jobs
        PERFORM cron.schedule('expire-registration-sessions', '*/5 * * * *', 'SELECT expire_old_registration_sessions();');
        PERFORM cron.schedule('cleanup-flow-tokens', '0 * * * *', 'SELECT cleanup_expired_flow_tokens();');
        PERFORM cron.schedule('cleanup-token-setup', '0 * * * *', 'SELECT cleanup_expired_token_setup();');
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        -- Ignore errors if pg_cron is not available
        NULL;
END $$;

-- ============================================
-- 6. COMMENTS FOR DOCUMENTATION
-- ============================================
COMMENT ON TABLE registration_sessions IS 'Registration sessions for backward compatibility with existing code';
COMMENT ON COLUMN registration_sessions.phone IS 'Phone number of the user registering';
COMMENT ON COLUMN registration_sessions.user_type IS 'Type of user (trainer or client)';
COMMENT ON COLUMN registration_sessions.registration_type IS 'Type of registration process';
COMMENT ON COLUMN registration_sessions.step IS 'Current step in the registration process';
COMMENT ON COLUMN registration_sessions.status IS 'Current status of the registration session';
COMMENT ON COLUMN registration_sessions.data IS 'Registration data collected so far';
COMMENT ON COLUMN registration_sessions.retry_count IS 'Number of retry attempts';
COMMENT ON COLUMN registration_sessions.needs_retry IS 'Whether this session needs to be retried';
COMMENT ON COLUMN registration_sessions.expires_at IS 'When this session expires';

COMMENT ON FUNCTION expire_old_registration_sessions() IS 'Expires old registration sessions and states';
COMMENT ON FUNCTION cleanup_expired_flow_tokens() IS 'Marks expired flow tokens as expired';
COMMENT ON FUNCTION cleanup_expired_token_setup() IS 'Marks expired token setup requests as expired';
COMMENT ON FUNCTION increment(INTEGER, UUID) IS 'Increments a value by 1 (utility function)';

-- ============================================
-- 7. DATA MIGRATION (if needed)
-- ============================================

-- Migrate existing registration_states to registration_sessions format if needed
INSERT INTO registration_sessions (
    phone, 
    user_type, 
    registration_type, 
    step, 
    status, 
    data, 
    completed_at, 
    created_at, 
    updated_at
)
SELECT 
    phone_number,
    user_type,
    user_type, -- registration_type same as user_type
    CASE 
        WHEN current_step = 0 THEN 'name'
        WHEN current_step = 1 THEN 'business_name'
        WHEN current_step = 2 THEN 'email'
        WHEN current_step = 3 THEN 'specialization'
        WHEN current_step = 4 THEN 'experience'
        WHEN current_step = 5 THEN 'location'
        WHEN current_step = 6 THEN 'pricing'
        ELSE 'unknown'
    END as step,
    CASE 
        WHEN completed = TRUE THEN 'completed'
        ELSE 'active'
    END as status,
    data,
    completed_at,
    created_at,
    updated_at
FROM registration_states
WHERE NOT EXISTS (
    SELECT 1 FROM registration_sessions rs 
    WHERE rs.phone = registration_states.phone_number 
    AND rs.user_type = registration_states.user_type
);

-- ============================================
-- 8. VALIDATION QUERIES
-- ============================================

-- Query to check migration success
-- SELECT 
--     'registration_sessions' as table_name,
--     COUNT(*) as row_count,
--     COUNT(DISTINCT phone) as unique_phones,
--     COUNT(*) FILTER (WHERE status = 'completed') as completed_count
-- FROM registration_sessions
-- UNION ALL
-- SELECT 
--     'registration_states' as table_name,
--     COUNT(*) as row_count,
--     COUNT(DISTINCT phone_number) as unique_phones,
--     COUNT(*) FILTER (WHERE completed = TRUE) as completed_count
-- FROM registration_states;