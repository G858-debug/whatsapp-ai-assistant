-- Create dashboard tokens table
CREATE TABLE IF NOT EXISTS dashboard_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    ip_address TEXT,
    user_agent TEXT
);

-- Create indexes
CREATE INDEX idx_dashboard_tokens_trainer_id ON dashboard_tokens(trainer_id);
CREATE INDEX idx_dashboard_tokens_token ON dashboard_tokens(token);
CREATE INDEX idx_dashboard_tokens_expires_at ON dashboard_tokens(expires_at);
CREATE INDEX idx_dashboard_tokens_revoked ON dashboard_tokens(revoked);

-- Add JWT secret to environment variables table if exists
-- Or store securely in your environment configuration