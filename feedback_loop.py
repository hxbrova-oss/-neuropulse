import requests
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
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
                    'temperature': 0.3,
                    'max_tokens': 512
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


def get_recent_posts(hours=24):
    since = quote((datetime.now(CET) - timedelta(hours=hours)).isoformat())
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.published&published_at=gte.{since}&order=published_at.desc',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f'Error fetching recent posts: {e}')
        return []


def get_tg_message_id(post_id):
    try:
        details = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?id=eq.{post_id}&select=message_id',
            headers=HDR, timeout=15
        ).json()
        if details and details[0].get('message_id'):
            return details[0]['message_id']
    except Exception:
        pass
    return None


def get_ig_post_id(post_id):
    return None


def extract_signals_from_post(post):
    text = post.get('telegram_post', '')[:500]
    category = post.get('post_type', 'news')
    prompt = f'''Analyze this tech post and classify what audience signal it sends.

Post text: {text}

Classify the expected audience reaction. Reply JSON only:
{{
  "signal": "positive|question|educational_need",
  "confidence": 0.0-1.0,
  "reason": "one-line explanation"
}}'''
    return call_mistral(prompt)


def save_signal(signal_type, count, category):
    today = datetime.now(CET).strftime('%Y-%m-%d')
    try:
        existing = requests.get(
            f'{SUPABASE_URL}/rest/v1/audience_signals?signal_type=eq.{signal_type}&topic_category=eq.{category}&date=eq.{today}',
            headers=HDR, timeout=15
        ).json()
        if existing:
            new_count = existing[0]['count'] + count
            requests.patch(
                f'{SUPABASE_URL}/rest/v1/audience_signals?id=eq.{existing[0]["id"]}',
                headers={**HDR, 'Content-Type': 'application/json'},
                json={'count': new_count}, timeout=15
            )
        else:
            requests.post(
                f'{SUPABASE_URL}/rest/v1/audience_signals',
                headers={**HDR, 'Content-Type': 'application/json'},
                json={'signal_type': signal_type, 'count': count, 'topic_category': category, 'date': today},
                timeout=15
            )
    except Exception as e:
        print(f'  Error saving signal: {e}')


def get_aggregated_signals():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/audience_signals',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        rows = res.json()
        totals = {}
        for r in rows:
            st = r['signal_type']
            totals[st] = totals.get(st, 0) + r['count']
        return totals
    except Exception:
        return {}


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Feedback Loop started...')

    posts = get_recent_posts(48)
    print(f'Analyzing {len(posts)} recent posts...')

    for post in posts:
        time.sleep(2)
        result = extract_signals_from_post(post)
        if result:
            save_signal(result['signal'], 1, post.get('post_type', 'news'))
            print(f'  Post "{post["title"][:40]}..." -> {result["signal"]} (conf: {result["confidence"]})')

    signals = get_aggregated_signals()
    total = sum(signals.values()) or 1
    print(f'\nAggregated signals:')
    for st, count in sorted(signals.items(), key=lambda x: -x[1]):
        pct = (count / total) * 100
        print(f'  {st}: {count} ({pct:.0f}%)')

    if signals.get('question', 0) / total > 0.3:
        print('\n[!] More than 30% questions -> increase educational content ratio')
    if signals.get('positive', 0) / total > 0.4:
        print('\n[+] More than 40% positive signals -> replicate current format')

    print('Feedback Loop done.')


if __name__ == '__main__':
    main()
