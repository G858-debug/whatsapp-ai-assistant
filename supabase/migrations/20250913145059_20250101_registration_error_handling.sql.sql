-- Add registration error tracking table
CREATE TABLE IF NOT EXISTS registration_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    error_id VARCHAR(50) NOT NULL,
    session_id UUID REFERENCES registration_sessions(id),
    phone VARCHAR(20),
    error_type VARCHAR(100),
    error_message TEXT,
    traceback TEXT,
    context JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add fields to registration_sessions for better tracking
ALTER TABLE registration_sessions 
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_error_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS expired_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS expiry_reason VARCHAR(50),
ADD COLUMN IF NOT EXISTS last_completed_step VARCHAR(50),
ADD COLUMN IF NOT EXISTS registration_state JSONB DEFAULT '{}';

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_registration_errors_session ON registration_errors(session_id);
CREATE INDEX IF NOT EXISTS idx_registration_errors_phone ON registration_errors(phone);
CREATE INDEX IF NOT EXISTS idx_registration_errors_created ON registration_errors(created_at);
CREATE INDEX IF NOT EXISTS idx_registration_sessions_expired ON registration_sessions(status, updated_at) 
WHERE status = 'active';

-- Add duplicate prevention constraints (if not exists)
ALTER TABLE trainers ADD CONSTRAINT unique_trainer_phone UNIQUE (whatsapp) 
ON CONFLICT DO NOTHING;
ALTER TABLE trainers ADD CONSTRAINT unique_trainer_email UNIQUE (email) 
ON CONFLICT DO NOTHING;
ALTER TABLE clients ADD CONSTRAINT unique_client_phone_trainer UNIQUE (whatsapp, trainer_id) 
ON CONFLICT DO NOTHING;

-- Rollback:
-- DROP TABLE IF EXISTS registration_errors;
-- ALTER TABLE registration_sessions 
--   DROP COLUMN IF EXISTS retry_count,
--   DROP COLUMN IF EXISTS last_error_at,
--   DROP COLUMN IF EXISTS expired_at,
--   DROP COLUMN IF EXISTS expiry_reason,
--   DROP COLUMN IF EXISTS last_completed_step,
--   DROP COLUMN IF EXISTS registration_state;
-- DROP INDEX IF EXISTS idx_registration_errors_session;
-- DROP INDEX IF EXISTS idx_registration_errors_phone;
-- DROP INDEX IF EXISTS idx_registration_errors_created;
-- DROP INDEX IF EXISTS idx_registration_sessions_expired;
-- ALTER TABLE trainers DROP CONSTRAINT IF EXISTS unique_trainer_phone;
-- ALTER TABLE trainers DROP CONSTRAINT IF EXISTS unique_trainer_email;
-- ALTER TABLE clients DROP CONSTRAINT IF EXISTS unique_client_phone_trainer;