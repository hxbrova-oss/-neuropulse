import requests
import json
import os
import re
import time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
MISTRAL_MODEL = os.getenv('MISTRAL_MODEL', 'mistral-large-latest')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}


def call_mistral(prompt, retries=2):
    for attempt in range(retries):
        try:
            res = requests.post(
                'https://api.mistral.ai/v1/chat/completions',
                headers={'Authorization': f'Bearer {MISTRAL_API_KEY}', 'Content-Type': 'application/json'},
                json={'model': MISTRAL_MODEL, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.3, 'max_tokens': 256},
                timeout=30
            )
            if res.status_code == 429:
                time.sleep((attempt + 1) * 10)
                continue
            res.raise_for_status()
            text = res.json()['choices'][0]['message']['content']
            cleaned = re.sub(r'```json\s*', '', text.strip())
            cleaned = re.sub(r'```\s*$', '', cleaned.strip())
            return json.loads(cleaned)
        except Exception:
            time.sleep(2)
    return None


def get_recent_titles(hours_back=48):
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue',
            params={'select': 'title,created_at', 'order': 'created_at.desc', 'limit': 30},
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        rows = res.json()
        return [r['title'] for r in rows if r.get('created_at', '') >= cutoff.isoformat()]
    except Exception as e:
        print(f'  Error fetching recent titles: {e}')
        return []


def is_semantic_duplicate(new_title, hours_back=48):
    recent = get_recent_titles(hours_back)
    if not recent:
        return False, None

    prompt = f'''Compare this new topic against recently published topics.
Reply JSON only: {{"is_duplicate": true/false, "similar_to": "title or null"}}

New topic: "{new_title}"

Recent topics:
{json.dumps(recent, indent=2)}

Is the new topic covering essentially the same story as any recent topic?'''
    result = call_mistral(prompt)
    if result and result.get('is_duplicate'):
        return True, result.get('similar_to')
    return False, None
