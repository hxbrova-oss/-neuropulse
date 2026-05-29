import requests
import json
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

CET = timezone(timedelta(hours=1))
HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}


def get_posts_24h_ago():
    since = quote((datetime.now(CET) - timedelta(hours=48)).isoformat())
    until = quote((datetime.now(CET) - timedelta(hours=24)).isoformat())
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.published&published_at=gte.{since}&published_at=lte.{until}&order=published_at.desc',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f'Error fetching posts: {e}')
        return []


def get_tg_stats(message_id):
    if not message_id:
        return None
    try:
        res = requests.get(
            f'https://api.telegram.org/bot{BOT_TOKEN}/getMessage',
            params={'chat_id': CHANNEL_ID, 'message_id': message_id},
            timeout=15
        )
        if res.ok:
            data = res.json()
            msg = data.get('result', {})
            return {
                'views': msg.get('views', 0),
                'forwards': msg.get('forwards', 0),
                'reactions': len(msg.get('reactions', [])),
            }
    except Exception:
        pass
    return None


def normalize_score(raw, max_raw):
    if max_raw == 0:
        return 0
    return round(min(raw / max_raw * 100, 100), 1)


def save_analytics(post, tg_stats):
    category = post.get('post_type', 'general')

    tg_score = normalize_score(
        (tg_stats.get('views', 0) * 1 +
         tg_stats.get('forwards', 0) * 3 +
         tg_stats.get('reactions', 0) * 2) if tg_stats else 0,
        500
    ) if tg_stats else 0

    ig_score = 0
    tt_score = 0

    raw = (tg_score + ig_score + tt_score)
    content_score = round(raw / 3, 1) if raw > 0 else 0

    try:
        payload = {
            'post_id': post['id'],
            'tg_score': tg_score,
            'ig_score': ig_score,
            'tt_score': tt_score,
            'content_score': content_score,
            'topic_category': category,
            'collected_at': datetime.now(CET).isoformat()
        }
        requests.post(
            f'{SUPABASE_URL}/rest/v1/cross_analytics',
            headers={**HDR, 'Content-Type': 'application/json'},
            json=payload, timeout=15
        )
        print(f'  Post "{post["title"][:40]}..." → content_score: {content_score}')
    except Exception as e:
        print(f'  Error saving analytics: {e}')

    return content_score


def get_top_categories():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/cross_analytics?order=content_score.desc&limit=20',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        rows = res.json()
        cats = {}
        for r in rows:
            cat = r['topic_category']
            if cat not in cats:
                cats[cat] = {'total_score': 0, 'count': 0}
            cats[cat]['total_score'] += r['content_score']
            cats[cat]['count'] += 1
        ranked = sorted(cats.items(), key=lambda x: -x[1]['total_score'] / x[1]['count'])
        return [(cat, round(data['total_score'] / data['count'], 1)) for cat, data in ranked]
    except Exception:
        return []


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Cross-Platform Analytics started...')

    posts = get_posts_24h_ago()
    print(f'Analyzing {len(posts)} posts published ~24h ago...')

    for post in posts:
        message_id = post.get('message_id')
        tg_stats = get_tg_stats(message_id)
        save_analytics(post, tg_stats)

    top = get_top_categories()
    if top:
        print(f'\nTop performing content categories:')
        for cat, avg in top[:5]:
            print(f'  {cat}: avg score {avg}/100')

    print('Cross-Platform Analytics done.')


if __name__ == '__main__':
    main()
