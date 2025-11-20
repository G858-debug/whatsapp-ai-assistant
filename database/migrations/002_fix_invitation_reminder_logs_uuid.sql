-- Fix invitation_reminder_logs.invitation_id to use UUID instead of BIGINT
-- This aligns with client_invitations.id which is UUID

-- Step 1: Drop the existing foreign key constraint
ALTER TABLE invitation_reminder_logs
DROP CONSTRAINT IF EXISTS fk_invitation;

-- Step 2: Drop the unique constraint (it will be recreated after type change)
ALTER TABLE invitation_reminder_logs
DROP CONSTRAINT IF EXISTS unique_invitation_reminder;

-- Step 3: Change the column type from BIGINT to UUID
-- Note: This assumes the table is empty or has been cleared before migration
-- If there's existing data, you may need to handle data migration separately
ALTER TABLE invitation_reminder_logs
ALTER COLUMN invitation_id TYPE UUID USING invitation_id::text::uuid;

-- Step 4: Recreate the foreign key constraint
ALTER TABLE invitation_reminder_logs
ADD CONSTRAINT fk_invitation
    FOREIGN KEY (invitation_id)
    REFERENCES client_invitations(id)
    ON DELETE CASCADE;

-- Step 5: Recreate the unique constraint
ALTER TABLE invitation_reminder_logs
ADD CONSTRAINT unique_invitation_reminder
    UNIQUE (invitation_id, reminder_type);

-- Add comment
COMMENT ON COLUMN invitation_reminder_logs.invitation_id IS 'UUID foreign key to client_invitations table';
