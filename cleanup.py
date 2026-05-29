import requests
import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

HDR = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}'
}

# Delete test row
print("Cleaning up test row...")
res = requests.delete(
    f"{SUPABASE_URL}/rest/v1/content_queue?id=eq.15",
    headers=HDR,
    timeout=10
)
print(f"Delete status: {res.status_code}")

# Delete duplicate pending
print("Cleaning up duplicate...")
res = requests.delete(
    f"{SUPABASE_URL}/rest/v1/content_queue?id=eq.16",
    headers=HDR,
    timeout=10
)
print(f"Delete status: {res.status_code}")

# Show final state
print("\n=== Final Content ===")
res = requests.get(
    f"{SUPABASE_URL}/rest/v1/content_queue?select=id,title,status,score&order=id.desc",
    headers=HDR,
    timeout=15
)
data = res.json()
for row in data:
    rid = row.get("id", "?")
    status = row.get("status", "?")
    score = row.get("score", "?")
    title = row.get("title", "")[:55]
    print(f"  {rid}. [{status}] {score}/10 - {title}")
