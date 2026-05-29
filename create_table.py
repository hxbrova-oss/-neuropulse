import requests
import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

sql = """
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
"""

sql_index1 = "CREATE INDEX IF NOT EXISTS idx_status ON content_queue(status);"
sql_index2 = "CREATE INDEX IF NOT EXISTS idx_created ON content_queue(created_at DESC);"
sql_index3 = "CREATE INDEX IF NOT EXISTS idx_score ON content_queue(score DESC);"

print('Creating table in Supabase...')

for label, query in [('table', sql), ('idx_status', sql_index1), ('idx_created', sql_index2), ('idx_score', sql_index3)]:
    try:
        res = requests.post(
            f'{SUPABASE_URL}/rest/v1/rpc/exec_sql',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json'
            },
            json={'query': query},
            timeout=30
        )
        print(f'{label}: {res.status_code} - {res.text[:200]}')
    except Exception as e:
        print(f'{label} error: {e}')
