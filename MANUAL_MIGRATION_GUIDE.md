# 🚀 **MANUAL MIGRATION REQUIRED**

## 📋 **Apply Flow Support Migration in Supabase**

Since the automated migration failed, you need to apply it manually in your Supabase dashboard:

### **Step 1: Go to Supabase Dashboard**
1. Open your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Create a new query

### **Step 2: Copy and Execute This SQL**

```sql
-- Migration: Add Flow Support Tables
-- Description: Creates tables for WhatsApp Flows tracking and management
-- Date: 2025-09-28

-- ============================================
-- 1. FLOW TOKENS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS flow_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL,
    flow_token VARCHAR(255) NOT NULL UNIQUE,
    flow_type VARCHAR(50) NOT NULL CHECK (flow_type IN ('trainer_onboarding', 'client_onboarding', 'assessment_flow', 'booking_flow')),
    flow_data JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'expired', 'cancelled')),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2. FLOW RESPONSES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS flow_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_token VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    flow_type VARCHAR(50) NOT NULL,
    response_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    screen_id VARCHAR(100),
    completed BOOLEAN DEFAULT FALSE,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 3. UPDATE TRAINERS TABLE FOR FLOW SUPPORT
-- ============================================
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS flow_token VARCHAR(255);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS onboarding_method VARCHAR(20) DEFAULT 'chat' CHECK (onboarding_method IN ('chat', 'flow'));
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS specialization VARCHAR(100);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS experience_years VARCHAR(20);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS available_days JSONB DEFAULT '[]'::jsonb;
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS preferred_time_slots VARCHAR(50);
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS notification_preferences JSONB DEFAULT '[]'::jsonb;
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE;
ALTER TABLE trainers ADD COLUMN IF NOT EXISTS marketing_consent BOOLEAN DEFAULT FALSE;

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX IF NOT EXISTS idx_flow_tokens_phone ON flow_tokens(phone_number);
CREATE INDEX IF NOT EXISTS idx_flow_tokens_token ON flow_tokens(flow_token);
CREATE INDEX IF NOT EXISTS idx_flow_tokens_type ON flow_tokens(flow_type);
CREATE INDEX IF NOT EXISTS idx_flow_responses_token ON flow_responses(flow_token);
CREATE INDEX IF NOT EXISTS idx_flow_responses_phone ON flow_responses(phone_number);
CREATE INDEX IF NOT EXISTS idx_trainers_flow_token ON trainers(flow_token);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================
ALTER TABLE flow_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE flow_responses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their flow tokens" ON flow_tokens
    FOR ALL USING (phone_number = current_setting('app.current_phone', true));

CREATE POLICY "Users can view their flow responses" ON flow_responses
    FOR SELECT USING (phone_number = current_setting('app.current_phone', true));

CREATE POLICY "Users can insert their flow responses" ON flow_responses
    FOR INSERT WITH CHECK (phone_number = current_setting('app.current_phone', true));
```

### **Step 3: Execute the Query**
1. Click **Run** to execute the migration
2. Verify that all tables were created successfully
3. Check that the trainers table has the new columns

### **Step 4: Verify Migration**
After applying the migration, you should see:
- ✅ `flow_tokens` table created
- ✅ `flow_responses` table created  
- ✅ `trainers` table enhanced with flow columns
- ✅ Indexes created for performance
- ✅ RLS policies applied

---

## 🎯 **After Migration is Applied**

Once you've applied the migration manually, the WhatsApp Flows system will be fully operational and ready to use!
