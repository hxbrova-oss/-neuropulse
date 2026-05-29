-- ============================================
-- NeuroPulse — Schema Migration
-- ============================================
-- Run this in Supabase > SQL Editor to add eu_angle column

-- Add eu_angle column if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'content_queue' AND column_name = 'eu_angle'
  ) THEN
    ALTER TABLE content_queue ADD COLUMN eu_angle TEXT;
  END IF;
END $$;

-- Add linkedin_post column if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'content_queue' AND column_name = 'linkedin_post'
  ) THEN
    ALTER TABLE content_queue ADD COLUMN linkedin_post TEXT;
  END IF;
END $$;

-- Update best_time comment
COMMENT ON COLUMN content_queue.best_time IS 'morning (7AM CET) | noon (12PM CET) | evening (7PM CET)';
