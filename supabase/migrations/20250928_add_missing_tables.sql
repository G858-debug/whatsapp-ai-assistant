-- Migration: Add Missing Tables (conversation_states, message_history)
-- Description: Creates tables needed for conversation management and message history
-- Date: 2025-09-28
-- Timezone: Africa/Johannesburg (SAST)

-- ============================================
-- 1. CONVERSATION STATES TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS conversation_states CASCADE;

CREATE TABLE conversation_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    current_state VARCHAR(50) DEFAULT 'idle',
    state_data JSONB DEFAULT '{}'::jsonb,
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2. MESSAGE HISTORY TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS message_history CASCADE;

CREATE TABLE message_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL,
    message_text TEXT NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'audio', 'document')),
    processed BOOLEAN DEFAULT FALSE,
    intent VARCHAR(50),
    confidence DECIMAL(3,2),
    ai_intent JSONB DEFAULT '{}'::jsonb,
    response_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Conversation states indexes
CREATE INDEX IF NOT EXISTS idx_conversation_states_phone ON conversation_states(phone_number);
CREATE INDEX IF NOT EXISTS idx_conversation_states_state ON conversation_states(current_state);
CREATE INDEX IF NOT EXISTS idx_conversation_states_activity ON conversation_states(last_activity);

-- Message history indexes
CREATE INDEX IF NOT EXISTS idx_message_history_phone ON message_history(phone_number);
CREATE INDEX IF NOT EXISTS idx_message_history_direction ON message_history(direction);
CREATE INDEX IF NOT EXISTS idx_message_history_created ON message_history(created_at);
CREATE INDEX IF NOT EXISTS idx_message_history_processed ON message_history(processed);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can manage their conversation states" ON conversation_states;
DROP POLICY IF EXISTS "Users can view their message history" ON message_history;
DROP POLICY IF EXISTS "Users can insert their message history" ON message_history;

-- Enable RLS on all tables
ALTER TABLE conversation_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_history ENABLE ROW LEVEL SECURITY;

-- Conversation states policies
CREATE POLICY "Users can manage their conversation states" ON conversation_states
    FOR ALL USING (phone_number = current_setting('app.current_phone', true));

-- Message history policies
CREATE POLICY "Users can view their message history" ON message_history
    FOR SELECT USING (phone_number = current_setting('app.current_phone', true));

CREATE POLICY "Users can insert their message history" ON message_history
    FOR INSERT WITH CHECK (phone_number = current_setting('app.current_phone', true));

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================
COMMENT ON TABLE conversation_states IS 'Tracks conversation state for each user';
COMMENT ON TABLE message_history IS 'Stores all WhatsApp messages processed by the AI assistant';

COMMENT ON COLUMN conversation_states.current_state IS 'Current conversation state (idle, registration, booking, etc.)';
COMMENT ON COLUMN conversation_states.state_data IS 'Additional data stored with the conversation state';
COMMENT ON COLUMN message_history.ai_intent IS 'AI understanding of the message intent';
COMMENT ON COLUMN message_history.response_data IS 'Response data sent back to user';
