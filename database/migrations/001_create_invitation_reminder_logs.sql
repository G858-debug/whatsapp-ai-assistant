-- Create invitation_reminder_logs table
-- This table tracks when reminders are sent for client invitations

CREATE TABLE IF NOT EXISTS invitation_reminder_logs (
    id BIGSERIAL PRIMARY KEY,
    invitation_id BIGINT NOT NULL,
    reminder_type VARCHAR(50) NOT NULL,  -- '24h_client', '72h_trainer', '7d_expiry'
    sent_to VARCHAR(255) NOT NULL,       -- Phone number that received the reminder
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Foreign key to client_invitations table
    CONSTRAINT fk_invitation
        FOREIGN KEY (invitation_id)
        REFERENCES client_invitations(id)
        ON DELETE CASCADE,

    -- Ensure we don't send the same reminder type twice for the same invitation
    CONSTRAINT unique_invitation_reminder
        UNIQUE (invitation_id, reminder_type)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_invitation_reminder_logs_invitation_id
    ON invitation_reminder_logs(invitation_id);

CREATE INDEX IF NOT EXISTS idx_invitation_reminder_logs_reminder_type
    ON invitation_reminder_logs(reminder_type);

CREATE INDEX IF NOT EXISTS idx_invitation_reminder_logs_sent_at
    ON invitation_reminder_logs(sent_at);

-- Add comment to table
COMMENT ON TABLE invitation_reminder_logs IS 'Tracks when invitation reminders (24h, 72h, 7d) are sent to clients and trainers';
COMMENT ON COLUMN invitation_reminder_logs.reminder_type IS 'Type of reminder: 24h_client, 72h_trainer, or 7d_expiry';
COMMENT ON COLUMN invitation_reminder_logs.sent_to IS 'Phone number that received the reminder';
