import requests
import json
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

# Check if eu_angle column exists by trying to query it
print('=== Checking eu_angle column ===')
try:
    res = requests.get(
        f'{SUPABASE_URL}/rest/v1/content_queue?select=eu_angle&limit=1',
        headers=HDR,
        timeout=10
    )
    print(f'Status: {res.status_code}')
    if res.status_code == 200:
        print('eu_angle column EXISTS')
    else:
        print(f'Error: {res.text[:300]}')
except Exception as e:
    print(f'Error: {e}')

# Try inserting without eu_angle
print('\n=== Testing insert without eu_angle ===')
try:
    res = requests.post(
        f'{SUPABASE_URL}/rest/v1/content_queue',
        headers=HDR,
        json={
            'title': 'Test topic - delete me',
            'source_url': 'https://example.com',
            'post_type': 'news',
            'score': 7,
            'status': 'pending',
        },
        timeout=15
    )
    print(f'Status: {res.status_code}')
    if res.status_code in [200, 201]:
        data = res.json()
        print(f'Inserted ID: {data[0]["id"] if data else "unknown"}')
        # Delete it
        if data:
            requests.delete(
                f'{SUPABASE_URL}/rest/v1/content_queue?id=eq.{data[0]["id"]}',
                headers=HDR,
                timeout=10
            )
            print('Deleted test row')
    else:
        print(f'Error: {res.text[:300]}')
except Exception as e:
    print(f'Error: {e}')

# Try inserting WITH eu_angle
print('\n=== Testing insert with eu_angle ===')
try:
    res = requests.post(
        f'{SUPABASE_URL}/rest/v1/content_queue',
        headers=HDR,
        json={
            'title': 'Test with eu_angle - delete me',
            'source_url': 'https://example.com',
            'eu_angle': 'Test angle',
            'post_type': 'news',
            'score': 7,
            'status': 'pending',
        },
        timeout=15
    )
    print(f'Status: {res.status_code}')
    if res.status_code in [200, 201]:
        data = res.json()
        print(f'Inserted with eu_angle!')
        if data:
            requests.delete(
                f'{SUPABASE_URL}/rest/v1/content_queue?id=eq.{data[0]["id"]}',
                headers=HDR,
                timeout=10
            )
            print('Deleted test row')
    else:
        print(f'Error: {res.text[:300]}')
except Exception as e:
    print(f'Error: {e}')
