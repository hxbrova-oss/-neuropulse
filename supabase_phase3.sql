-- ============================================
-- NeuroPulse — Phase 3: Real-Time Intelligence
-- Run in Supabase > SQL Editor
-- ============================================

-- Trend velocity tracking
CREATE TABLE IF NOT EXISTS trend_history (
    id SERIAL PRIMARY KEY,
    trend_name VARCHAR(200),
    source VARCHAR(50),
    volume INTEGER,
    velocity FLOAT,
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- AI Tools Database
CREATE TABLE IF NOT EXISTS ai_tools_db (
    id SERIAL PRIMARY KEY,
    tool_name VARCHAR(200) UNIQUE,
    description TEXT,
    category VARCHAR(50),
    pricing VARCHAR(20),
    best_for VARCHAR(50),
    wow_factor TEXT,
    affiliate_url TEXT,
    affiliate_potential BOOLEAN DEFAULT false,
    votes INTEGER DEFAULT 0,
    weekly_featured BOOLEAN DEFAULT false,
    added_at TIMESTAMP DEFAULT NOW()
);

-- Breaking News Log
CREATE TABLE IF NOT EXISTS breaking_news_log (
    id SERIAL PRIMARY KEY,
    title TEXT,
    source VARCHAR(100),
    published_at TIMESTAMP DEFAULT NOW(),
    platforms_published TEXT,
    engagement_score FLOAT
);

-- Verify
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
