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

HDR = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}'
}

AFFILIATE_SOURCES = [
    'Notion (notion.so/product/notion-ai)',
    'Cursor AI (cursor.com)',
    'Zapier (zapier.com)',
    'Coursera (coursera.org)',
    'Udemy (udemy.com)',
    'DigitalOcean (digitalocean.com)',
]


def call_mistral(prompt, retries=3):
    for attempt in range(retries):
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
                    'temperature': 0.8,
                    'max_tokens': 2048
                },
                timeout=60
            )
            if res.status_code == 429:
                wait = (attempt + 1) * 10
                print(f'  Rate limited, waiting {wait}s...')
                time.sleep(wait)
                continue
            res.raise_for_status()
            text = res.json()['choices'][0]['message']['content']
            cleaned = re.sub(r'```json\s*', '', text.strip())
            cleaned = re.sub(r'```\s*$', '', cleaned.strip())
            return json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                return json.loads(text)
            except Exception:
                return None
        except Exception as e:
            print(f'  Mistral error (attempt {attempt+1}): {e}')
            time.sleep(5)
    return None


def get_pending():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.pending&order=score.desc&limit=3',
            headers=HDR,
            timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f'Error fetching pending topics: {e}')
        return []


def get_breaking_priority():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.pending&order=score.desc&limit=1',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        rows = res.json()
        if rows and rows[0].get('post_type') in ('model_launch', 'breaking'):
            return [rows[0]]
        return None
    except Exception:
        return None


def generate_post(topic):
    prompt = f'''You are a multi-platform content creator for "NeuroPulse" — a tech channel targeting English-speaking professionals in Central Europe (DE, CH, AT, NL). Age 25-40: developers, SaaS founders, AI enthusiasts.

Generate content for ALL platforms from this single topic:

Title: {topic["title"]}
Angle: {topic.get("eu_angle", topic.get("arabic_angle", "General tech news"))}
Type: {topic.get("post_type", "news")}

PLATFORMS TO GENERATE:

1. TELEGRAM POST (200-350 words):
- Hook line → Context → 3-4 value bullets → CTA
- Professional, specific, no fluff
- Bold key terms with **markdown**
- Include #AITools #Automation #TechEU #Productivity

2. TWITTER/X POST (max 280 chars):
- Hook + key insight + CTA
- Punchy, concise

3. INSTAGRAM CAPTION (max 2200 chars):
- Hook (first line — no hashtags, no emoji overload)
- 3-4 value lines (specific, actionable)
- CTA line
- 20-25 hashtags at the end (mix: #AITools #TechEU #SaaS #Automation + niche tags)
- Write for visual learners, slightly more casual than Telegram

4. TIKTOK SCRIPT (30-45 seconds, max 120 words):
- Hook: provocative question or bold claim (first 3 seconds)
- 3 fast value points (spoken, conversational)
- CTA: "Follow for more"
- Write exactly as it would be SPOKEN, not read
- No hashtags in the script itself

Reply with JSON only:
{{
  "telegram_post": "Full Telegram post",
  "instagram_caption": "Instagram caption with 20-25 hashtags at end",
  "tiktok_script": "Spoken script for 30-45 second video",
  "hashtags": ["AITools", "Automation", "TechEU", "Productivity"],
  "best_time": "morning|noon|evening"
}}'''
    return call_mistral(prompt)


def update_status(topic_id, post_data):
    try:
        payload = {
            'status': 'ready',
            'telegram_post': post_data['telegram_post'],
            'instagram_caption': post_data.get('instagram_caption', ''),
            'tiktok_script': post_data.get('tiktok_script', ''),
            'hashtags': json.dumps(post_data['hashtags']),
            'best_time': post_data['best_time'],
        }
        res = requests.patch(
            f'{SUPABASE_URL}/rest/v1/content_queue?id=eq.{topic_id}',
            headers={**HDR, 'Content-Type': 'application/json'},
            json=payload,
            timeout=15
        )
        res.raise_for_status()
        return True
    except Exception as e:
        print(f'Error updating status: {e}')
        return False


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Production Engine started...')

    breaking = get_breaking_priority()
    if breaking:
        print(f'Breaking priority topic found: {breaking[0]["title"][:60]}')
        pending = breaking
    else:
        pending = get_pending()
    print(f'Found {len(pending)} pending topics (3 sources: main + AI news + trends)')

    produced = 0
    for topic in pending:
        time.sleep(3)
        post_data = generate_post(topic)
        if post_data and update_status(topic['id'], post_data):
            produced += 1
            print(f'Produced: {topic["title"][:60]}')
            if post_data.get('telegram_post'):
                print(f'  Telegram preview: {post_data["telegram_post"][:100]}...')
            if post_data.get('tiktok_script'):
                print(f'  TikTok script: {len(post_data["tiktok_script"])} chars')
            if post_data.get('instagram_caption'):
                print(f'  Instagram caption: {len(post_data["instagram_caption"])} chars')
        else:
            print(f'Failed: {topic["title"][:60]}')

    print(f'Production done. Produced {produced} posts.')


if __name__ == '__main__':
    main()
