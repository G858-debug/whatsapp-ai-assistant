-- Migration: Social Media Performance Tracking Tables
-- Description: Creates social media tables including performance tracking, A/B testing, trending topics, and hashtag analytics
-- Date: 2025-01-03
-- Timezone: Africa/Johannesburg (SAST)

-- ============================================
-- 1. SOCIAL POSTS TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS social_posts CASCADE;

CREATE TABLE social_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    platform VARCHAR(50) NOT NULL DEFAULT 'facebook' CHECK (platform IN ('facebook', 'instagram', 'twitter', 'linkedin', 'tiktok')),
    scheduled_time TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'scheduled', 'published', 'failed')),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    template_id UUID,
    facebook_post_id VARCHAR(100),
    published_time TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2. SOCIAL IMAGES TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS social_images CASCADE;

CREATE TABLE social_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    image_type VARCHAR(50) DEFAULT 'photo' CHECK (image_type IN ('photo', 'graphic', 'infographic', 'meme', 'quote')),
    file_size INTEGER DEFAULT 0,
    dimensions JSONB DEFAULT '{}',
    alt_text TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 3. SOCIAL ANALYTICS TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS social_analytics CASCADE;

CREATE TABLE social_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 4. POSTING SCHEDULE TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS posting_schedule CASCADE;

CREATE TABLE posting_schedule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_number INTEGER NOT NULL CHECK (week_number >= 1 AND week_number <= 52),
    posts_per_day INTEGER DEFAULT 1 CHECK (posts_per_day >= 1 AND posts_per_day <= 10),
    posting_times JSONB DEFAULT '["09:00"]',
    platforms JSONB DEFAULT '["facebook"]',
    content_types JSONB DEFAULT '["motivational"]',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 5. CONTENT TEMPLATES TABLE
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS content_templates CASCADE;

CREATE TABLE content_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_type VARCHAR(50) NOT NULL CHECK (template_type IN ('motivational', 'educational', 'promotional', 'fitness_tip', 'nutrition', 'success_story')),
    title VARCHAR(200) NOT NULL,
    content_template TEXT NOT NULL,
    variables JSONB DEFAULT '{}',
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 6. CONTENT PERFORMANCE TABLE (NEW)
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS content_performance CASCADE;

CREATE TABLE content_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hook_type VARCHAR(50) NOT NULL,
    opening_line TEXT NOT NULL,
    engagement_rate DECIMAL(5,2) NOT NULL,
    share_count INTEGER DEFAULT 0,
    virality_score DECIMAL(5,2) DEFAULT 0.00,
    best_performing_hour INTEGER CHECK (best_performing_hour >= 0 AND best_performing_hour <= 23),
    audience_sentiment VARCHAR(20) CHECK (audience_sentiment IN ('positive', 'negative', 'neutral', 'mixed')),
    post_id UUID REFERENCES social_posts(id) ON DELETE SET NULL,
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 7. AB_TESTS TABLE (NEW)
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS ab_tests CASCADE;

CREATE TABLE ab_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variant_a_id UUID NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
    variant_b_id UUID NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
    winner_id UUID REFERENCES social_posts(id) ON DELETE SET NULL,
    metric_tested VARCHAR(50) NOT NULL CHECK (metric_tested IN ('engagement_rate', 'reach', 'shares', 'clicks', 'conversions')),
    performance_difference DECIMAL(5,2) DEFAULT 0.00,
    test_duration_hours INTEGER NOT NULL CHECK (test_duration_hours > 0),
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'cancelled')),
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 8. TRENDING TOPICS TABLE (NEW)
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS trending_topics CASCADE;

CREATE TABLE trending_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic VARCHAR(200) NOT NULL,
    relevance_score DECIMAL(5,2) NOT NULL CHECK (relevance_score >= 0.00 AND relevance_score <= 100.00),
    content_generated BOOLEAN DEFAULT FALSE,
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    expiry_time TIMESTAMPTZ NOT NULL,
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 9. HASHTAG PERFORMANCE TABLE (NEW)
-- ============================================
-- Drop existing table if it exists (for clean migration)
DROP TABLE IF EXISTS hashtag_performance CASCADE;

CREATE TABLE hashtag_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hashtag VARCHAR(100) NOT NULL,
    avg_reach INTEGER DEFAULT 0,
    avg_engagement DECIMAL(5,2) DEFAULT 0.00,
    last_used TIMESTAMPTZ,
    performance_trend VARCHAR(20) DEFAULT 'stable' CHECK (performance_trend IN ('rising', 'falling', 'stable', 'volatile')),
    usage_count INTEGER DEFAULT 0,
    trainer_id UUID NOT NULL REFERENCES trainers(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Social posts indexes
CREATE INDEX IF NOT EXISTS idx_social_posts_trainer ON social_posts(trainer_id);
CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON social_posts(platform);
CREATE INDEX IF NOT EXISTS idx_social_posts_status ON social_posts(status);
CREATE INDEX IF NOT EXISTS idx_social_posts_scheduled_time ON social_posts(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_social_posts_created_at ON social_posts(created_at);

-- Social images indexes
CREATE INDEX IF NOT EXISTS idx_social_images_post ON social_images(post_id);
CREATE INDEX IF NOT EXISTS idx_social_images_type ON social_images(image_type);

-- Social analytics indexes
CREATE INDEX IF NOT EXISTS idx_social_analytics_post ON social_analytics(post_id);
CREATE INDEX IF NOT EXISTS idx_social_analytics_engagement ON social_analytics(engagement_rate);
CREATE INDEX IF NOT EXISTS idx_social_analytics_created_at ON social_analytics(created_at);

-- Posting schedule indexes
CREATE INDEX IF NOT EXISTS idx_posting_schedule_week ON posting_schedule(week_number);
CREATE INDEX IF NOT EXISTS idx_posting_schedule_active ON posting_schedule(is_active);

-- Content templates indexes
CREATE INDEX IF NOT EXISTS idx_content_templates_type ON content_templates(template_type);
CREATE INDEX IF NOT EXISTS idx_content_templates_active ON content_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_content_templates_priority ON content_templates(priority);

-- Content performance indexes
CREATE INDEX IF NOT EXISTS idx_content_performance_hook_type ON content_performance(hook_type);
CREATE INDEX IF NOT EXISTS idx_content_performance_engagement ON content_performance(engagement_rate);
CREATE INDEX IF NOT EXISTS idx_content_performance_virality ON content_performance(virality_score);
CREATE INDEX IF NOT EXISTS idx_content_performance_trainer ON content_performance(trainer_id);
CREATE INDEX IF NOT EXISTS idx_content_performance_hour ON content_performance(best_performing_hour);

-- AB tests indexes
CREATE INDEX IF NOT EXISTS idx_ab_tests_variant_a ON ab_tests(variant_a_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_variant_b ON ab_tests(variant_b_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_winner ON ab_tests(winner_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_status ON ab_tests(status);
CREATE INDEX IF NOT EXISTS idx_ab_tests_trainer ON ab_tests(trainer_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_started_at ON ab_tests(started_at);

-- Trending topics indexes
CREATE INDEX IF NOT EXISTS idx_trending_topics_topic ON trending_topics(topic);
CREATE INDEX IF NOT EXISTS idx_trending_topics_relevance ON trending_topics(relevance_score);
CREATE INDEX IF NOT EXISTS idx_trending_topics_expiry ON trending_topics(expiry_time);
CREATE INDEX IF NOT EXISTS idx_trending_topics_trainer ON trending_topics(trainer_id);
CREATE INDEX IF NOT EXISTS idx_trending_topics_discovered ON trending_topics(discovered_at);

-- Hashtag performance indexes
CREATE INDEX IF NOT EXISTS idx_hashtag_performance_hashtag ON hashtag_performance(hashtag);
CREATE INDEX IF NOT EXISTS idx_hashtag_performance_engagement ON hashtag_performance(avg_engagement);
CREATE INDEX IF NOT EXISTS idx_hashtag_performance_trend ON hashtag_performance(performance_trend);
CREATE INDEX IF NOT EXISTS idx_hashtag_performance_trainer ON hashtag_performance(trainer_id);
CREATE INDEX IF NOT EXISTS idx_hashtag_performance_last_used ON hashtag_performance(last_used);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Trainers can manage their social posts" ON social_posts;
DROP POLICY IF EXISTS "Trainers can manage their social images" ON social_images;
DROP POLICY IF EXISTS "Trainers can manage their social analytics" ON social_analytics;
DROP POLICY IF EXISTS "Trainers can manage posting schedule" ON posting_schedule;
DROP POLICY IF EXISTS "Trainers can manage content templates" ON content_templates;
DROP POLICY IF EXISTS "Trainers can manage content performance" ON content_performance;
DROP POLICY IF EXISTS "Trainers can manage ab tests" ON ab_tests;
DROP POLICY IF EXISTS "Trainers can manage trending topics" ON trending_topics;
DROP POLICY IF EXISTS "Trainers can manage hashtag performance" ON hashtag_performance;

-- Enable RLS on all tables
ALTER TABLE social_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE posting_schedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE ab_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE trending_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE hashtag_performance ENABLE ROW LEVEL SECURITY;

-- Social posts policies
CREATE POLICY "Trainers can manage their social posts" ON social_posts
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- Social images policies
CREATE POLICY "Trainers can manage their social images" ON social_images
    FOR ALL USING (
        post_id IN (
            SELECT id FROM social_posts 
            WHERE trainer_id IN (
                SELECT id FROM trainers 
                WHERE whatsapp = current_setting('app.current_phone', true)
            )
        )
    );

-- Social analytics policies
CREATE POLICY "Trainers can manage their social analytics" ON social_analytics
    FOR ALL USING (
        post_id IN (
            SELECT id FROM social_posts 
            WHERE trainer_id IN (
                SELECT id FROM trainers 
                WHERE whatsapp = current_setting('app.current_phone', true)
            )
        )
    );

-- Posting schedule policies
CREATE POLICY "Trainers can manage posting schedule" ON posting_schedule
    FOR ALL USING (true); -- Global access for now, can be restricted later

-- Content templates policies
CREATE POLICY "Trainers can manage content templates" ON content_templates
    FOR ALL USING (true); -- Global access for now, can be restricted later

-- Content performance policies
CREATE POLICY "Trainers can manage content performance" ON content_performance
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- AB tests policies
CREATE POLICY "Trainers can manage ab tests" ON ab_tests
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- Trending topics policies
CREATE POLICY "Trainers can manage trending topics" ON trending_topics
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- Hashtag performance policies
CREATE POLICY "Trainers can manage hashtag performance" ON hashtag_performance
    FOR ALL USING (
        trainer_id IN (
            SELECT id FROM trainers 
            WHERE whatsapp = current_setting('app.current_phone', true)
        )
    );

-- ============================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================
COMMENT ON TABLE social_posts IS 'Social media posts created by trainers';
COMMENT ON TABLE social_images IS 'Images associated with social media posts';
COMMENT ON TABLE social_analytics IS 'Analytics data for social media posts';
COMMENT ON TABLE posting_schedule IS 'Posting schedule configuration for different weeks';
COMMENT ON TABLE content_templates IS 'Reusable content templates for social media posts';
COMMENT ON TABLE content_performance IS 'Performance tracking for different content hooks and patterns';
COMMENT ON TABLE ab_tests IS 'A/B testing data for social media content variants';
COMMENT ON TABLE trending_topics IS 'Trending topics discovered for content generation';
COMMENT ON TABLE hashtag_performance IS 'Performance analytics for hashtags used in posts';

COMMENT ON COLUMN social_posts.platform IS 'Social media platform where the post will be published';
COMMENT ON COLUMN social_posts.status IS 'Current status of the post in the publishing pipeline';
COMMENT ON COLUMN social_analytics.engagement_rate IS 'Calculated engagement rate as percentage';
COMMENT ON COLUMN content_performance.virality_score IS 'Score indicating how viral the content performed';
COMMENT ON COLUMN content_performance.best_performing_hour IS 'Hour of day (0-23) when content performs best';
COMMENT ON COLUMN ab_tests.performance_difference IS 'Percentage difference in performance between variants';
COMMENT ON COLUMN trending_topics.relevance_score IS 'Relevance score from 0-100 for the topic';
COMMENT ON COLUMN hashtag_performance.performance_trend IS 'Trend direction for hashtag performance over time';