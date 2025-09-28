-- Migration: Core Tables (trainers, clients, habits)
-- Description: Creates the fundamental tables needed for the WhatsApp AI Assistant
-- Date: 2025-09-28
-- Timezone: Africa/Johannesburg (SAST)

-- ============================================
-- 1. TRAINERS TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS trainers CASCADE;

CREATE TABLE trainers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    whatsapp VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    pricing_per_session DECIMAL(10,2) DEFAULT 500.00,
    subscription_status VARCHAR(50) DEFAULT 'free' CHECK (subscription_status IN ('free', 'premium', 'pro')),
    subscription_expires_at TIMESTAMPTZ,
    subscription_end TIMESTAMPTZ, -- For test compatibility
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2. CLIENTS TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS clients CASCADE;

CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    whatsapp VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    package_type VARCHAR(50) DEFAULT 'single' CHECK (package_type IN ('single', 'package_5', 'package_10', 'package_20')),
    sessions_remaining INTEGER DEFAULT 1,
    custom_price_per_session DECIMAL(10,2),
    last_session_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique client per trainer
    CONSTRAINT unique_client_per_trainer UNIQUE (trainer_id, whatsapp)
);

-- ============================================
-- 3. BOOKINGS TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS bookings CASCADE;

CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    session_datetime TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER DEFAULT 60,
    price DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled', 'no_show')),
    session_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 4. HABITS TABLE (for test compatibility)
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS habits CASCADE;

CREATE TABLE habits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    habit_type VARCHAR(50) NOT NULL CHECK (habit_type IN (
        'water_intake', 'sleep_hours', 'steps', 'calories', 
        'workout_completed', 'meals_logged', 'weight', 'mood'
    )),
    value TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 5. HABIT_TRACKING TABLE (for actual usage)
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS habit_tracking CASCADE;

CREATE TABLE habit_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    habit_type VARCHAR(50) NOT NULL CHECK (habit_type IN (
        'water_intake', 'sleep_hours', 'steps', 'calories', 
        'workout_completed', 'meals_logged', 'weight', 'mood'
    )),
    value TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one entry per client per habit type per day
    CONSTRAINT unique_habit_per_day UNIQUE (client_id, habit_type, date)
);

-- ============================================
-- 6. MESSAGES TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS messages CASCADE;

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID REFERENCES trainers(id),
    client_id UUID REFERENCES clients(id),
    phone_number VARCHAR(20) NOT NULL,
    message_text TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text' CHECK (message_type IN ('text', 'image', 'audio', 'video')),
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 7. WORKOUTS TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS workouts CASCADE;

CREATE TABLE workouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    workout_type VARCHAR(50) DEFAULT 'general' CHECK (workout_type IN ('strength', 'cardio', 'flexibility', 'general')),
    duration_minutes INTEGER DEFAULT 60,
    difficulty_level VARCHAR(20) DEFAULT 'medium' CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    exercises JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 8. ASSESSMENTS TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS assessments CASCADE;

CREATE TABLE assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    assessment_type VARCHAR(50) NOT NULL CHECK (assessment_type IN ('initial', 'progress', 'final')),
    questions JSONB NOT NULL DEFAULT '{}',
    answers JSONB NOT NULL DEFAULT '{}',
    score DECIMAL(5,2),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Trainers indexes
CREATE INDEX IF NOT EXISTS idx_trainers_whatsapp ON trainers(whatsapp);
CREATE INDEX IF NOT EXISTS idx_trainers_email ON trainers(LOWER(email));
CREATE INDEX IF NOT EXISTS idx_trainers_status ON trainers(status);

-- Clients indexes
CREATE INDEX IF NOT EXISTS idx_clients_trainer ON clients(trainer_id);
CREATE INDEX IF NOT EXISTS idx_clients_whatsapp ON clients(whatsapp);
CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);
CREATE INDEX IF NOT EXISTS idx_clients_last_session ON clients(last_session_date);

-- Bookings indexes
CREATE INDEX IF NOT EXISTS idx_bookings_trainer ON bookings(trainer_id);
CREATE INDEX IF NOT EXISTS idx_bookings_client ON bookings(client_id);
CREATE INDEX IF NOT EXISTS idx_bookings_datetime ON bookings(session_datetime);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);

-- Habits table indexes
CREATE INDEX IF NOT EXISTS idx_habits_trainer ON habits(trainer_id);
CREATE INDEX IF NOT EXISTS idx_habits_client ON habits(client_id);
CREATE INDEX IF NOT EXISTS idx_habits_date ON habits(date);
CREATE INDEX IF NOT EXISTS idx_habits_type ON habits(habit_type);

-- Habit tracking indexes
CREATE INDEX IF NOT EXISTS idx_habit_tracking_client ON habit_tracking(client_id);
CREATE INDEX IF NOT EXISTS idx_habit_tracking_date ON habit_tracking(date);
CREATE INDEX IF NOT EXISTS idx_habit_tracking_type ON habit_tracking(habit_type);
CREATE INDEX IF NOT EXISTS idx_habit_tracking_client_date ON habit_tracking(client_id, date);

-- Messages indexes
CREATE INDEX IF NOT EXISTS idx_messages_phone ON messages(phone_number);
CREATE INDEX IF NOT EXISTS idx_messages_trainer ON messages(trainer_id);
CREATE INDEX IF NOT EXISTS idx_messages_client ON messages(client_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);

-- Workouts indexes
CREATE INDEX IF NOT EXISTS idx_workouts_trainer ON workouts(trainer_id);
CREATE INDEX IF NOT EXISTS idx_workouts_client ON workouts(client_id);
CREATE INDEX IF NOT EXISTS idx_workouts_type ON workouts(workout_type);
CREATE INDEX IF NOT EXISTS idx_workouts_difficulty ON workouts(difficulty_level);

-- Assessments indexes
CREATE INDEX IF NOT EXISTS idx_assessments_client ON assessments(client_id);
CREATE INDEX IF NOT EXISTS idx_assessments_type ON assessments(assessment_type);
CREATE INDEX IF NOT EXISTS idx_assessments_completed ON assessments(completed_at);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Trainers can view own data" ON trainers;
DROP POLICY IF EXISTS "Clients can view own data" ON clients;
DROP POLICY IF EXISTS "Trainers can manage their clients" ON clients;
DROP POLICY IF EXISTS "Trainers can manage their bookings" ON bookings;
DROP POLICY IF EXISTS "Clients can view their bookings" ON bookings;
DROP POLICY IF EXISTS "Trainers can manage their habits" ON habits;
DROP POLICY IF EXISTS "Clients can view their habits" ON habits;
DROP POLICY IF EXISTS "Clients can manage their habits" ON habit_tracking;
DROP POLICY IF EXISTS "Trainers can view client habits" ON habit_tracking;
DROP POLICY IF EXISTS "Trainers can manage their workouts" ON workouts;
DROP POLICY IF EXISTS "Clients can view their workouts" ON workouts;
DROP POLICY IF EXISTS "Users can view their messages" ON messages;
DROP POLICY IF EXISTS "Users can insert their messages" ON messages;
DROP POLICY IF EXISTS "Clients can manage their assessments" ON assessments;
DROP POLICY IF EXISTS "Trainers can view client assessments" ON assessments;

-- Enable RLS on all tables
ALTER TABLE trainers ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE habits ENABLE ROW LEVEL SECURITY;
ALTER TABLE habit_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE workouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;

-- Trainers can see their own data
CREATE POLICY "Trainers can view own data" ON trainers
    FOR ALL USING (whatsapp = current_setting('app.current_phone', true));

-- Clients can see their own data
CREATE POLICY "Clients can view own data" ON clients
    FOR ALL USING (whatsapp = current_setting('app.current_phone', true));

-- Trainers can manage their clients
CREATE POLICY "Trainers can manage their clients" ON clients
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- Bookings policies
CREATE POLICY "Trainers can manage their bookings" ON bookings
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Clients can view their bookings" ON bookings
    FOR SELECT USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- Habits table policies
CREATE POLICY "Trainers can manage their habits" ON habits
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Clients can view their habits" ON habits
    FOR SELECT USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- Habit tracking policies
CREATE POLICY "Clients can manage their habits" ON habit_tracking
    FOR ALL USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Trainers can view client habits" ON habit_tracking
    FOR SELECT USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE trainer_id IN (
                SELECT id FROM trainers 
                WHERE whatsapp = current_setting('app.current_phone', true)
            )
        )
    );

-- Workout policies
CREATE POLICY "Trainers can manage their workouts" ON workouts
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Clients can view their workouts" ON workouts
    FOR SELECT USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- Messages policies
CREATE POLICY "Users can view their messages" ON messages
    FOR SELECT USING (
        phone_number = current_setting('app.current_phone', true)
    );

CREATE POLICY "Users can insert their messages" ON messages
    FOR INSERT WITH CHECK (
        phone_number = current_setting('app.current_phone', true)
    );

-- Assessments policies
CREATE POLICY "Clients can manage their assessments" ON assessments
    FOR ALL USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

CREATE POLICY "Trainers can view client assessments" ON assessments
    FOR SELECT USING (
        client_id IN (
            SELECT id FROM clients 
            WHERE trainer_id IN (
                SELECT id FROM trainers 
                WHERE whatsapp = current_setting('app.current_phone', true)
            )
        )
    );

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================
COMMENT ON TABLE trainers IS 'Personal trainers using the WhatsApp AI Assistant';
COMMENT ON TABLE clients IS 'Clients of trainers using the system';
COMMENT ON TABLE bookings IS 'Scheduled training sessions between trainers and clients';
COMMENT ON TABLE habits IS 'Habit tracking table for test compatibility';
COMMENT ON TABLE habit_tracking IS 'Daily habit and metric tracking for clients';
COMMENT ON TABLE workouts IS 'Workout plans and exercises for clients';
COMMENT ON TABLE messages IS 'WhatsApp messages processed by the AI assistant';
COMMENT ON TABLE assessments IS 'Client assessments and progress tracking';

COMMENT ON COLUMN trainers.pricing_per_session IS 'Default price per training session in ZAR';
COMMENT ON COLUMN clients.sessions_remaining IS 'Number of sessions left in current package';
COMMENT ON COLUMN clients.custom_price_per_session IS 'Custom price override for this client';
COMMENT ON COLUMN habit_tracking.value IS 'Habit value stored as text to accommodate different data types';
COMMENT ON COLUMN messages.direction IS 'Whether message was sent to or received from WhatsApp';
