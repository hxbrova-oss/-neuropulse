-- ============================================
-- نظام الربح المؤتمت - Supabase Schema
-- ============================================
-- انسخ هذا الكود كاملاً والصقه في Supabase > SQL Editor ثم Execute

CREATE TABLE IF NOT EXISTS content_queue (
  id            SERIAL PRIMARY KEY,
  title         TEXT NOT NULL,
  source_url    TEXT,
  arabic_angle  TEXT,
  post_type     VARCHAR(50),
  score         INTEGER,
  status        VARCHAR(20) DEFAULT 'pending',
  telegram_post TEXT,
  twitter_post  TEXT,
  facebook_post TEXT,
  hashtags      TEXT,
  best_time     VARCHAR(20),
  image_prompt  TEXT,
  created_at    TIMESTAMP DEFAULT NOW(),
  published_at  TIMESTAMP,
  views         INTEGER DEFAULT 0,
  engagement    INTEGER DEFAULT 0
);

-- فهارس للأداء
CREATE INDEX IF NOT EXISTS idx_status ON content_queue(status);
CREATE INDEX IF NOT EXISTS idx_created ON content_queue(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_score ON content_queue(score DESC);

-- ============================================
-- شرح الحقول:
-- status: pending → ready → published
-- score: من 1-10 يقرره الذكاء الاصطناعي (7+ فقط يُكمل)
-- arabic_angle: الزاوية المحلية التي اقترحها AI
-- best_time: morning / afternoon / evening للنشر
-- ============================================
