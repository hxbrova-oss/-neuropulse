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
                headers={'Authorization': f'Bearer {MISTRAL_API_KEY}', 'Content-Type': 'application/json'},
                json={'model': MISTRAL_MODEL, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.9, 'max_tokens': 1024},
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
    hooks_raw = post.get('hook_variations', '')
    if isinstance(hooks_raw, str):
        try:
            hooks = json.loads(hooks_raw) if hooks_raw.startswith('[') else []
        except Exception:
            hooks = []
    else:
        hooks = hooks_raw

    prompt = f'''You are Alex, a Berlin-based AI engineer with strong opinions.

Title: {post.get('title', '')}

Generate 3 hook variations in Alex's voice — direct, opinionated, no hype.

Requirements:
- Variation A: curiosity — tease something the reader is missing
- Variation B: contrarian — challenge a common belief
- Variation C: data/shock — a surprising number or bold claim

Reply JSON only:
{{
  "variation_a": "curiosity hook in Alex's voice",
  "variation_b": "contrarian hook in Alex's voice",
  "variation_c": "data/shock hook in Alex's voice"
}}'''
    return call_mistral(prompt)


def save_ab_test(post_id, var_a, var_b, var_c):
    try:
        payload = {
            'post_id': post_id,
            'variation_a': var_a,
            'variation_b': var_b,
            'variation_c': var_c,
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
        print(f'  AB test (3 hooks) saved for post {post_id}')
        return True
    except Exception as e:
        print(f'  Error saving AB test: {e}')
        return False


def count_tests():
    try:
        res = requests.get(f'{SUPABASE_URL}/rest/v1/ab_tests?select=count', headers=HDR, timeout=15)
        res.raise_for_status()
        return len(res.json())
    except Exception:
        return 0


def get_winning_style():
    try:
        res = requests.get(f'{SUPABASE_URL}/rest/v1/ab_tests?select=winner&winner=neq.', headers=HDR, timeout=15)
        res.raise_for_status()
        rows = res.json()
        if not rows:
            return None
        wins = {'A': 0, 'B': 0, 'C': 0}
        for r in rows:
            w = r.get('winner', '')
            if w in wins:
                wins[w] += 1
        return max(wins, key=wins.get)
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

    save_ab_test(
        post_id,
        variants.get('variation_a', ''),
        variants.get('variation_b', ''),
        variants.get('variation_c', '')
    )

    total = count_tests()
    print(f'Total AB tests stored: {total}')

    if total >= 50:
        style = get_winning_style()
        if style:
            label = {'A': 'curiosity', 'B': 'contrarian', 'C': 'data/shock'}
            print(f'50+ tests done. Winning hook type: {label.get(style, style)}')
            print(f'  Alex persona will favor {label.get(style, style)} hooks going forward')

    print('AB Tester done.')


if __name__ == '__main__':
    main()
