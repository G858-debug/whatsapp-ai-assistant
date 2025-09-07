-- Add challenge progress tracking tables
CREATE TABLE IF NOT EXISTS challenge_progress (
    id uuid DEFAULT extensions.uuid_generate_v4() PRIMARY KEY,
    challenge_id uuid REFERENCES challenges(id) ON DELETE CASCADE,
    participant_id uuid REFERENCES challenge_participants(id) ON DELETE CASCADE,
    value_achieved float NOT NULL DEFAULT 0,
    logged_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_challenge_progress_challenge ON challenge_progress(challenge_id);
CREATE INDEX IF NOT EXISTS idx_challenge_progress_participant ON challenge_progress(participant_id);
CREATE INDEX IF NOT EXISTS idx_challenge_progress_logged_at ON challenge_progress(logged_at);

-- Add trigger for updated_at
CREATE TRIGGER set_challenge_progress_updated_at
    BEFORE UPDATE ON challenge_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();