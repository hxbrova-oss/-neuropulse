import requests
import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}

# Check eu_angle
res = requests.get(
    f'{SUPABASE_URL}/rest/v1/content_queue?select=eu_angle,linkedin_post&limit=1',
    headers=HDR, timeout=10
)
if res.status_code == 200:
    print('eu_angle: EXISTS')
else:
    print(f'eu_angle: {res.status_code}')

# Current content
res2 = requests.get(
    f'{SUPABASE_URL}/rest/v1/content_queue?select=id,title,status,score&order=id.desc',
    headers=HDR, timeout=10
)
data = res2.json()
print(f'\nCurrent rows: {len(data)}')
for r in data:
    print(f'  {r["id"]}. [{r["status"]}] {r["score"]}/10 - {r["title"][:50]}')
