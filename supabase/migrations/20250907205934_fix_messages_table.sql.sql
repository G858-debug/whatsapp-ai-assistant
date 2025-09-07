-- Check if messages table has content column, if not rename message to content
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'messages' 
        AND column_name = 'content'
    ) THEN
        -- Check if message column exists and rename it
        IF EXISTS (
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'messages' 
            AND column_name = 'message'
        ) THEN
            ALTER TABLE messages RENAME COLUMN message TO content;
        END IF;
    END IF;
END $$;

-- Ensure messages table has proper structure
ALTER TABLE messages ADD COLUMN IF NOT EXISTS content TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS trainer_id UUID REFERENCES trainers(id);
ALTER TABLE messages ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES clients(id);
ALTER TABLE messages ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_messages_trainer_created ON messages(trainer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_client_created ON messages(client_id, created_at DESC);