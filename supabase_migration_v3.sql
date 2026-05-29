-- ============================================
-- NeuroPulse — Migration v3 (Instagram Reels)
-- Run in Supabase > SQL Editor
-- ============================================

-- Remove image columns (no longer needed)
ALTER TABLE content_queue DROP COLUMN IF EXISTS instagram_image_url;
ALTER TABLE content_queue DROP COLUMN IF EXISTS image_prompt;

-- Add video path/url columns (shared TG → TT → IG flow)
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS video_path TEXT;
ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS video_url TEXT;

-- Verify
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'content_queue'
ORDER BY ordinal_position;
