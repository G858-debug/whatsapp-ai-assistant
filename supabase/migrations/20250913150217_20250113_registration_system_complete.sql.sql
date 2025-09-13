-- Migration: Complete Registration System Tables
-- Description: Adds all tables needed for robust registration with duplicate prevention and error recovery

-- 1. Registration sessions table (for maintaining registration state)
CREATE TABLE IF NOT EXISTS registration_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) NOT NULL,
    registration_type VARCHAR(20) NOT NULL CHECK (registration_type IN ('trainer', 'client', 'unknown')),
    step VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'abandoned', 'error')),
    data JSONB DEFAULT '{}',
    retry_count INTEGER DEFAULT 0,
    needs_retry BOOLEAN DEFAULT FALSE,
    last_error_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for registration sessions
CREATE INDEX idx_registration_sessions_phone ON registration_sessions(phone);
CREATE INDEX idx_registration_sessions_status ON registration_sessions(status);
CREATE INDEX idx_registration_sessions_expires ON registration_sessions(expires_at);
CREATE INDEX idx_registration_sessions_needs_retry ON registration_sessions(needs_retry) WHERE needs_retry = TRUE;

-- 2. Registration attempts table (for tracking duplicate attempts)
CREATE TABLE IF NOT EXISTS registration_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) NOT NULL,
    user_type VARCHAR(20) CHECK (user_type IN ('trainer', 'client')),
    existing_user_id UUID,
    attempt_type VARCHAR(50) CHECK (attempt_type IN ('new', 'duplicate', 'retry', 'abandoned')),
    attempt_data JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for registration attempts
CREATE INDEX idx_registration_attempts_phone ON registration_attempts(phone);
CREATE INDEX idx_registration_attempts_user ON registration_attempts(existing_user_id);
CREATE INDEX idx_registration_attempts_created ON registration_attempts(created_at);

-- 3. Activity logs table (for tracking user activities including logins)
CREATE TABLE IF NOT EXISTS activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('trainer', 'client')),
    activity_type VARCHAR(50) NOT NULL,
    activity_data JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for activity logs
CREATE INDEX idx_activity_logs_user ON activity_logs(user_id, user_type);
CREATE INDEX idx_activity_logs_type ON activity_logs(activity_type);
CREATE INDEX idx_activity_logs_created ON activity_logs(created_at);

-- 4. Token setup requests table (for payment setup)
CREATE TABLE IF NOT EXISTS token_setup_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    setup_code VARCHAR(20) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'expired', 'cancelled')),
    token_id UUID,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for token setup
CREATE INDEX idx_token_setup_trainer ON token_setup_requests(trainer_id);
CREATE INDEX idx_token_setup_client ON token_setup_requests(client_id);
CREATE INDEX idx_token_setup_code ON token_setup_requests(setup_code);
CREATE INDEX idx_token_setup_status ON token_setup_requests(status);

-- 5. Client payment tokens table
CREATE TABLE IF NOT EXISTS client_payment_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    trainer_id UUID REFERENCES trainers(id) ON DELETE CASCADE,
    payfast_token VARCHAR(255),
    payfast_token_status VARCHAR(20) DEFAULT 'active' CHECK (payfast_token_status IN ('active', 'inactive', 'expired')),
    card_last_four VARCHAR(4),
    card_brand VARCHAR(20),
    consent_given BOOLEAN DEFAULT FALSE,
    consent_date TIMESTAMPTZ,
    consent_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for payment tokens
CREATE INDEX idx_payment_tokens_client ON client_payment_tokens(client_id);
CREATE INDEX idx_payment_tokens_trainer ON client_payment_tokens(trainer_id);
CREATE INDEX idx_payment_tokens_status ON client_payment_tokens(payfast_token_status);

-- 6. Archive tables for merged accounts
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

-- 7. Add missing columns to existing tables if they don't exist
DO $$ 
BEGIN
    -- Add custom_price_per_session to clients table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'clients' AND column_name = 'custom_price_per_session'
    ) THEN
        ALTER TABLE clients ADD COLUMN custom_price_per_session DECIMAL(10,2);
    END IF;
    
    -- Add subscription fields to trainers if they don't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trainers' AND column_name = 'subscription_status'
    ) THEN
        ALTER TABLE trainers ADD COLUMN subscription_status VARCHAR(50) DEFAULT 'free';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trainers' AND column_name = 'subscription_expires_at'
    ) THEN
        ALTER TABLE trainers ADD COLUMN subscription_expires_at TIMESTAMPTZ;
    END IF;
END $$;

-- 8. Create function to auto-expire old registration sessions
CREATE OR REPLACE FUNCTION expire_old_registration_sessions()
RETURNS void AS $$
BEGIN
    UPDATE registration_sessions
    SET status = 'abandoned'
    WHERE status = 'in_progress' 
    AND expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- 9. Create function to increment retry count
CREATE OR REPLACE FUNCTION increment(x INTEGER, row_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN x + 1;
END;
$$ LANGUAGE plpgsql;

-- 10. Row Level Security (RLS) Policies

-- Enable RLS on new tables
ALTER TABLE registration_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE registration_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE token_setup_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_payment_tokens ENABLE ROW LEVEL SECURITY;

-- Registration sessions - trainers can see their own
CREATE POLICY "Trainers can view own registration sessions"
    ON registration_sessions FOR SELECT
    USING (
        phone IN (
            SELECT whatsapp FROM trainers 
            WHERE id = auth.uid()
        )
    );

-- Registration sessions - clients can see their own
CREATE POLICY "Clients can view own registration sessions"
    ON registration_sessions FOR SELECT
    USING (
        phone IN (
            SELECT whatsapp FROM clients 
            WHERE id = auth.uid()
        )
    );

-- Activity logs - users can see their own
CREATE POLICY "Users can view own activity logs"
    ON activity_logs FOR SELECT
    USING (user_id = auth.uid());

-- Token setup - trainers can manage
CREATE POLICY "Trainers can manage token setup requests"
    ON token_setup_requests FOR ALL
    USING (trainer_id = auth.uid());

-- Token setup - clients can view their own
CREATE POLICY "Clients can view own token setup"
    ON token_setup_requests FOR SELECT
    USING (client_id = auth.uid());

-- Payment tokens - trainers can view their clients'
CREATE POLICY "Trainers can view client payment tokens"
    ON client_payment_tokens FOR SELECT
    USING (trainer_id = auth.uid());

-- Payment tokens - clients can manage their own
CREATE POLICY "Clients can manage own payment tokens"
    ON client_payment_tokens FOR ALL
    USING (client_id = auth.uid());

-- 11. Create scheduled job to expire sessions (if using pg_cron)
-- Note: This requires pg_cron extension to be enabled
-- SELECT cron.schedule('expire-registration-sessions', '*/5 * * * *', 'SELECT expire_old_registration_sessions();');

-- 12. Create indexes for better query performance
CREATE INDEX idx_trainers_whatsapp ON trainers(whatsapp);
CREATE INDEX idx_trainers_email ON trainers(LOWER(email));
CREATE INDEX idx_clients_whatsapp ON clients(whatsapp);
CREATE INDEX idx_clients_email ON clients(LOWER(email));
CREATE INDEX idx_clients_trainer ON clients(trainer_id);

-- 13. Add trigger to update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_registration_sessions_updated_at 
    BEFORE UPDATE ON registration_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_client_payment_tokens_updated_at 
    BEFORE UPDATE ON client_payment_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Rollback commands (commented for safety):
-- DROP TABLE IF EXISTS registration_sessions CASCADE;
-- DROP TABLE IF EXISTS registration_attempts CASCADE;
-- DROP TABLE IF EXISTS activity_logs CASCADE;
-- DROP TABLE IF EXISTS token_setup_requests CASCADE;
-- DROP TABLE IF EXISTS client_payment_tokens CASCADE;
-- DROP TABLE IF EXISTS trainers_archive CASCADE;
-- DROP TABLE IF EXISTS clients_archive CASCADE;
-- DROP FUNCTION IF EXISTS expire_old_registration_sessions();
-- DROP FUNCTION IF EXISTS increment(INTEGER, UUID);
-- DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
-- ALTER TABLE clients DROP COLUMN IF EXISTS custom_price_per_session;
-- ALTER TABLE trainers DROP COLUMN IF EXISTS subscription_status;
-- ALTER TABLE trainers DROP COLUMN IF EXISTS subscription_expires_at;