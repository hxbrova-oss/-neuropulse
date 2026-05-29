import feedparser
import requests
import json
import os
import re
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
MISTRAL_MODEL = os.getenv('MISTRAL_MODEL', 'mistral-large-latest')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

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
        print(f'  API status: {res.status_code}')
        if res.status_code == 200:
            text = res.json()['choices'][0]['message']['content']
            cleaned = re.sub(r'```json\s*', '', text.strip())
            cleaned = re.sub(r'```\s*$', '', cleaned.strip())
            return json.loads(cleaned)
        else:
            print(f'  Error: {res.text[:300]}')
            return None
    except Exception as e:
        print(f'  Error: {e}')
        return None

# Test 1: Fetch one RSS feed
print('=== Test 1: Fetching RSS ===')
feed = feedparser.parse('https://feeds.feedburner.com/TechCrunch')
print(f'Entries: {len(feed.entries)}')
entry = feed.entries[0]
topic = {
    'title': entry.title,
    'summary': entry.get('summary', '')[:500],
    'link': entry.link,
}
print(f'Topic: {topic["title"][:60]}')

# Test 2: Score with Mistral
print('\n=== Test 2: Scoring ===')
prompt = f'''قيّم هذا الموضوع من 1-10 للجمهور العربي:
العنوان: {topic["title"]}
الملخص: {topic["summary"]}
أجب بـ JSON فقط: {{"score": N, "arabic_angle": "زاوية", "post_type": "خبر"}}'''

score_data = call_mistral(prompt)
if score_data:
    print(f'Score: {score_data.get("score", "?")}/10')
    print(f'Angle: {score_data.get("arabic_angle", "")[:60]}')
else:
    print('Failed to score')
    exit()

# Test 3: Save to Supabase
if score_data.get('score', 0) >= 7:
    print('\n=== Test 3: Saving to Supabase ===')
    payload = {
        'title': topic['title'],
        'source_url': topic['link'],
        'arabic_angle': score_data.get('arabic_angle', ''),
        'post_type': score_data.get('post_type', 'خبر'),
        'score': score_data['score'],
        'status': 'pending',
        'created_at': datetime.now().isoformat()
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
    print(f'Status: {res.status_code}')
    if res.status_code in [200, 201]:
        print('Saved!')
else:
    print(f'\nScore too low ({score_data.get("score", 0)}), skipping.')

# Test 4: Generate post
if score_data.get('score', 0) >= 7:
    print('\n=== Test 4: Generating post ===')
    time.sleep(2)
    prompt2 = f'''اكتب منشوراً احترافياً بالعربية عن:
العنوان: {topic["title"]}
الزاوية: {score_data.get("arabic_angle", "")}

أجب بـ JSON فقط:
{{
  "telegram_post": "منشور 150 كلمة مع إيموجي",
  "hashtags": ["tag1","tag2","tag3"],
  "best_time": "morning"
}}'''
    post_data = call_mistral(prompt2)
    if post_data:
        print(f'Post: {post_data.get("telegram_post", "")[:150]}...')
        print(f'Hashtags: {post_data.get("hashtags", [])}')
        
        # Save post to Supabase
        print('\nSaving post...')
        res = requests.patch(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.pending&limit=1',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'status': 'ready',
                'telegram_post': post_data.get('telegram_post', ''),
                'hashtags': json.dumps(post_data.get('hashtags', [])),
                'best_time': post_data.get('best_time', 'morning'),
            },
            timeout=15
        )
        print(f'Save status: {res.status_code}')
    else:
        print('Failed to generate post')

print('\n=== DONE ===')
