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

# Step 1: Add eu_angle column via RPC
print('=== Adding eu_angle column ===')
try:
    res = requests.post(
        f'{SUPABASE_URL}/rest/v1/rpc/exec',
        headers=HDR,
        json={
            'query': 'ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS eu_angle TEXT;'
        },
        timeout=15
    )
    print(f'ALTER result: {res.status_code} - {res.text[:200]}')
except Exception as e:
    print(f'Error: {e}')

# Step 2: Add linkedin_post column
print('\n=== Adding linkedin_post column ===')
try:
    res = requests.post(
        f'{SUPABASE_URL}/rest/v1/rpc/exec',
        headers=HDR,
        json={
            'query': 'ALTER TABLE content_queue ADD COLUMN IF NOT EXISTS linkedin_post TEXT;'
        },
        timeout=15
    )
    print(f'ALTER result: {res.status_code} - {res.text[:200]}')
except Exception as e:
    print(f'Error: {e}')

# Step 3: Check current data
print('\n=== Current data ===')
try:
    res = requests.get(
        f'{SUPABASE_URL}/rest/v1/content_queue?select=id,title,status,score',
        headers=HDR,
        timeout=15
    )
    if res.status_code == 200:
        data = res.json()
        if isinstance(data, list):
            print(f'Total rows: {len(data)}')
            for row in data:
                print(f'  ID={row.get("id")} [{row.get("status")}] score={row.get("score")} | {row.get("title","")[:50]}')
        else:
            print(f'Response: {res.text[:300]}')
    else:
        print(f'Error: {res.status_code} - {res.text[:300]}')
except Exception as e:
    print(f'Error: {e}')

# Step 4: Delete all old bad content
print('\n=== Clearing old content ===')
try:
    res = requests.delete(
        f'{SUPABASE_URL}/rest/v1/content_queue?id=gt.0',
        headers=HDR,
        timeout=15
    )
    print(f'Delete result: {res.status_code}')
except Exception as e:
    print(f'Error: {e}')

# Step 5: Verify empty
print('\n=== Verifying empty table ===')
try:
    res = requests.get(
        f'{SUPABASE_URL}/rest/v1/content_queue?select=count',
        headers={**HDR, 'Prefer': 'count=exact'},
        timeout=15
    )
    print(f'Result: {res.status_code} - {res.text[:200]}')
except Exception as e:
    print(f'Error: {e}')
