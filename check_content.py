import requests
import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

res = requests.get(
    f'{SUPABASE_URL}/rest/v1/content_queue?select=id,title,status,telegram_post,score&order=id.desc&limit=5',
    headers={
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}'
    },
    timeout=15
)

data = res.json()
for row in data:
    rid = row.get("id", "?")
    status = row.get("status", "?")
    score = row.get("score", "?")
    title = row.get("title", "")[:60]
    post = row.get("telegram_post", "")
    
    print(f"ID={rid} [{status}] score={score}")
    print(f"Title: {title}")
    if post:
        print(f"Post preview:\n{post[:300]}...")
    print()
