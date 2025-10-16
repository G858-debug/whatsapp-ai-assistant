-- Migration: Phase 1 - Database Schema Enhancement for Feature 2
-- Date: 2025-01-17
-- Description: Complete database schema updates for trainer-client management system

-- 1.1 Add Missing Client Fields
ALTER TABLE clients ADD COLUMN IF NOT EXISTS experience_level VARCHAR(50);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS health_conditions TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS preferred_training_times TEXT; -- Replace generic 'availability'

-- 1.2 Add Client-Trainer Connection Management Fields
ALTER TABLE clients ADD COLUMN IF NOT EXISTS connection_status VARCHAR(20) DEFAULT 'active';
ALTER TABLE clients ADD COLUMN IF NOT EXISTS requested_by VARCHAR(20) DEFAULT 'client'; -- 'trainer' or 'client'
ALTER TABLE clients ADD COLUMN IF NOT EXISTS invitation_token VARCHAR(255);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS invited_at TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;

-- 1.3 Add Constraints
ALTER TABLE clients ADD CONSTRAINT clients_connection_status_check 
    CHECK (connection_status IN ('pending', 'active', 'declined', 'expired'));
ALTER TABLE clients ADD CONSTRAINT clients_requested_by_check 
    CHECK (requested_by IN ('trainer', 'client'));

-- 1.4 Create Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_clients_experience_level ON clients(experience_level);
CREATE INDEX IF NOT EXISTS idx_clients_connection_status ON clients(connection_status);
CREATE INDEX IF NOT EXISTS idx_clients_invitation_token ON clients(invitation_token);
CREATE INDEX IF NOT EXISTS idx_clients_trainer_status ON clients(trainer_id, connection_status);

-- 1.5 Create Client Invitations Table
CREATE TABLE IF NOT EXISTS client_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    client_phone VARCHAR(20) NOT NULL,
    client_name VARCHAR(255),
    client_email VARCHAR(255),
    invitation_token VARCHAR(255) UNIQUE NOT NULL,
    invitation_method VARCHAR(20) DEFAULT 'whatsapp', -- 'whatsapp', 'email', 'manual'
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined', 'expired')),
    message TEXT, -- Custom invitation message from trainer
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_trainer_client_invitation UNIQUE (trainer_id, client_phone)
);

-- 1.6 Create Indexes for Client Invitations
CREATE INDEX IF NOT EXISTS idx_client_invitations_trainer ON client_invitations(trainer_id);
CREATE INDEX IF NOT EXISTS idx_client_invitations_status ON client_invitations(status);
CREATE INDEX IF NOT EXISTS idx_client_invitations_token ON client_invitations(invitation_token);
CREATE INDEX IF NOT EXISTS idx_client_invitations_expires ON client_invitations(expires_at);

-- 1.7 Add Comments for Documentation
COMMENT ON COLUMN clients.experience_level IS 'Client fitness experience level: Beginner, Intermediate, Advanced, or Athlete';
COMMENT ON COLUMN clients.health_conditions IS 'Client health conditions, injuries, or medical considerations';
COMMENT ON COLUMN clients.preferred_training_times IS 'Client preferred training times (replaces generic availability)';
COMMENT ON COLUMN clients.connection_status IS 'Status of trainer-client connection: pending, active, declined, expired';
COMMENT ON COLUMN clients.requested_by IS 'Who initiated the connection: trainer or client';
COMMENT ON COLUMN clients.invitation_token IS 'Unique token for invitation tracking';

COMMENT ON TABLE client_invitations IS 'Manages trainer invitations to potential clients';

-- 1.8 Update Existing Data
UPDATE clients 
SET experience_level = 'Beginner' 
WHERE experience_level IS NULL;

UPDATE clients 
SET health_conditions = 'None specified' 
WHERE health_conditions IS NULL;

UPDATE clients 
SET preferred_training_times = availability 
WHERE preferred_training_times IS NULL AND availability IS NOT NULL;

UPDATE clients 
SET connection_status = 'active' 
WHERE connection_status IS NULL;

UPDATE clients 
SET requested_by = 'client' 
WHERE requested_by IS NULL;