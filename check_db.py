import requests
import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

HDR = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

# Step 1: Check current data
print('=== Current data in Supabase ===')
try:
    res = requests.get(
        f'{SUPABASE_URL}/rest/v1/content_queue?select=id,title,status,score,telegram_post,eu_angle',
        headers=HDR,
        timeout=15
    )
    data = res.json()
    print(f'Total rows: {len(data)}')
    for row in data:
        print(f'  [{row["status"]}] score={row.get("score","?")} | {row["title"][:50]}')
        if row.get("telegram_post"):
            print(f'    Post preview: {row["telegram_post"][:80]}...')
except Exception as e:
    print(f'Error: {e}')

# Step 2: Check if eu_angle column exists
print('\n=== Checking columns ===')
try:
    res = requests.get(
        f'{SUPABASE_URL}/rest/v1/content_queue?select=eu_angle&limit=1',
        headers=HDR,
        timeout=10
    )
    if res.status_code == 200:
        print('eu_angle column exists')
    else:
        print(f'eu_angle check: {res.status_code} - {res.text[:200]}')
except Exception as e:
    print(f'Error: {e}')
