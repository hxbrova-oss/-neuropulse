-- ============================================
-- NeuroPulse — Phase 2: Growth & Self-Improvement
-- Run in Supabase > SQL Editor
-- ============================================

-- 1. AB Tests
CREATE TABLE IF NOT EXISTS ab_tests (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES content_queue(id),
    variation_a TEXT,
    variation_b TEXT,
    winner VARCHAR(1),
    engagement_a INTEGER DEFAULT 0,
    engagement_b INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Hashtag Scores
CREATE TABLE IF NOT EXISTS hashtag_scores (
    tag VARCHAR(100) PRIMARY KEY,
    score FLOAT DEFAULT 0,
    times_used INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- 3. Audience Signals
CREATE TABLE IF NOT EXISTS audience_signals (
    id SERIAL PRIMARY KEY,
    signal_type VARCHAR(50),
    count INTEGER DEFAULT 0,
    topic_category VARCHAR(100),
    date DATE DEFAULT CURRENT_DATE
);

-- 4. Timing Heatmap
CREATE TABLE IF NOT EXISTS timing_heatmap (
    hour_cet INTEGER,
    day_of_week INTEGER,
    avg_engagement FLOAT DEFAULT 0,
    sample_count INTEGER DEFAULT 0,
    PRIMARY KEY (hour_cet, day_of_week)
);

-- 5. Cross-Platform Analytics
CREATE TABLE IF NOT EXISTS cross_analytics (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES content_queue(id),
    tg_score FLOAT,
    ig_score FLOAT,
    tt_score FLOAT,
    content_score FLOAT,
    topic_category VARCHAR(100),
    collected_at TIMESTAMP DEFAULT NOW()
);

-- Verify
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
