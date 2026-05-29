import feedparser
import requests
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
MISTRAL_MODEL = os.getenv('MISTRAL_MODEL', 'mistral-large-latest')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

CET = timezone(timedelta(hours=1))

RSS_FEEDS = [
    'https://feeds.feedburner.com/TechCrunch',
    'https://venturebeat.com/category/ai/feed/',
    'https://www.theverge.com/rss/index.xml',
    'https://hnrss.org/frontpage',
]

def call_mistral(prompt):
    try:
        res = requests.post(
            'https://api.mistral.ai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {MISTRAL_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': MISTRAL_MODEL,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.7,
                'max_tokens': 1024
            },
            timeout=60
        )
        if res.status_code == 200:
            text = res.json()['choices'][0]['message']['content']
            cleaned = re.sub(r'```json\s*', '', text.strip())
            cleaned = re.sub(r'```\s*$', '', cleaned.strip())
            return json.loads(cleaned)
        else:
            print(f'  API error: {res.status_code}')
            return None
    except Exception as e:
        print(f'  Error: {e}')
        return None

# Step 1: Fetch 3 topics from one RSS
print('=== Step 1: Fetching RSS ===')
feed = feedparser.parse(RSS_FEEDS[0])
topics = []
for entry in feed.entries[:3]:
    topics.append({
        'title': entry.title,
        'summary': entry.get('summary', '')[:500],
        'link': entry.link,
    })
print(f'Got {len(topics)} topics')

# Step 2: Score each topic
print('\n=== Step 2: Scoring ===')
saved_ids = []
for i, topic in enumerate(topics):
    print(f'\nTopic {i+1}: {topic["title"][:60]}')
    prompt = f'''Score this topic 1-10 for English-speaking tech professionals in Central Europe (DE, CH, AT, NL).
Title: {topic["title"]}
Summary: {topic["summary"]}
Reply JSON only: {{"score": N, "eu_angle": "angle for EU audience", "post_type": "news|tutorial|opinion"}}'''
    
    score_data = call_mistral(prompt)
    time.sleep(3)
    
    if score_data and score_data.get('score', 0) >= 7:
        print(f'  Score: {score_data["score"]}/10 - SAVING')
        payload = {
            'title': topic['title'],
            'source_url': topic['link'],
            'arabic_angle': score_data.get('eu_angle', score_data.get('arabic_angle', '')),
            'post_type': score_data.get('post_type', 'news'),
            'score': score_data['score'],
            'status': 'pending',
            'created_at': datetime.now(CET).isoformat()
        }
        res = requests.post(
            f'{SUPABASE_URL}/rest/v1/content_queue',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=15
        )
        if res.status_code in [200, 201]:
            try:
                data = res.json()
                if data:
                    saved_ids.append(data[0].get('id'))
            except Exception:
                saved_ids.append('saved')
            print(f'  Saved to Supabase (status {res.status_code})')
        else:
            print(f'  Save failed: {res.status_code} - {res.text[:200]}')
    else:
        score = score_data.get('score', '?') if score_data else '?'
        print(f'  Score: {score} - SKIPPED')

print(f'\nSaved {len(saved_ids)} topics')
print(f'Saved IDs: {saved_ids}')
