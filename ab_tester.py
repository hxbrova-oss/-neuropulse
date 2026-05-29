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
HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}


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
                    'temperature': 0.9,
                    'max_tokens': 1024
                },
                timeout=60
            )
            if res.status_code == 429:
                time.sleep((attempt + 1) * 10)
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


def get_last_published():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.published&order=published_at.desc&limit=1',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        rows = res.json()
        return rows[0] if rows else None
    except Exception as e:
        print(f'Error fetching last post: {e}')
        return None


def generate_variations(post):
    prompt = f'''You are a conversion copywriter. Generate 2 hook variations for this post.

Title: {post.get("title", "")}
Telegram post first 200 chars: {post.get("telegram_post", "")[:200]}

Requirements:
- Variation A: curiosity-based hook (tease, question, incomplete info)
- Variation B: data/shock-based hook (stat, bold claim, urgent)

Reply JSON only:
{{
  "variation_a": "curiosity hook line",
  "variation_b": "data/shock hook line"
}}'''
    return call_mistral(prompt)


def save_ab_test(post_id, var_a, var_b):
    try:
        payload = {
            'post_id': post_id,
            'variation_a': var_a,
            'variation_b': var_b,
            'winner': '',
            'engagement_a': 0,
            'engagement_b': 0
        }
        res = requests.post(
            f'{SUPABASE_URL}/rest/v1/ab_tests',
            headers={**HDR, 'Content-Type': 'application/json'},
            json=payload, timeout=15
        )
        res.raise_for_status()
        print(f'  AB test saved for post {post_id}')
        return True
    except Exception as e:
        print(f'  Error saving AB test: {e}')
        return False


def count_tests():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/ab_tests?select=count',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        return len(res.json())
    except Exception:
        return 0


def get_winning_style():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/ab_tests?select=winner&winner=neq.',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        rows = res.json()
        if not rows:
            return None
        wins_a = sum(1 for r in rows if r.get('winner') == 'A')
        wins_b = sum(1 for r in rows if r.get('winner') == 'B')
        return 'curiosity' if wins_a >= wins_b else 'data_shock'
    except Exception:
        return None


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] AB Tester Engine started...')

    post = get_last_published()
    if not post:
        print('No published posts found.')
        return

    post_id = post['id']
    existing = requests.get(
        f'{SUPABASE_URL}/rest/v1/ab_tests?post_id=eq.{post_id}&select=id',
        headers=HDR, timeout=15
    ).json()
    if existing:
        print(f'AB test already exists for post {post_id}. Skipping.')
        return

    print(f'Generating hook variations for: {post["title"][:60]}')
    time.sleep(2)
    variants = generate_variations(post)
    if not variants:
        print('Failed to generate variations.')
        return

    save_ab_test(post_id, variants['variation_a'], variants['variation_b'])

    total = count_tests()
    print(f'Total AB tests stored: {total}')

    if total >= 20:
        style = get_winning_style()
        if style:
            print(f'20+ tests done. Winning hook style: {style}')
            print(f'  (Update production_engine.py prompt manually to favor {style} hooks)')

    print('AB Tester done.')


if __name__ == '__main__':
    main()
