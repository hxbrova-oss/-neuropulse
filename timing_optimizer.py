import requests
import json
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

CET = timezone(timedelta(hours=1))
HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}


def get_published_posts():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.published&order=published_at.desc',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f'Error fetching posts: {e}')
        return []


def build_heatmap(posts):
    heatmap = {}
    for post in posts:
        pub_str = post.get('published_at')
        if not pub_str:
            continue
        try:
            pub = datetime.fromisoformat(pub_str.replace('Z', '+00:00')).astimezone(CET)
            hour = pub.hour
            dow = pub.weekday()
            key = (hour, dow)
            if key not in heatmap:
                heatmap[key] = {'total': 0, 'count': 0}
            heatmap[key]['count'] += 1
            heatmap[key]['total'] += post.get('score', 5)
        except Exception:
            continue
    return heatmap


def save_heatmap(heatmap):
    for (hour, dow), data in heatmap.items():
        avg = round(data['total'] / data['count'], 2) if data['count'] > 0 else 0
        try:
            existing = requests.get(
                f'{SUPABASE_URL}/rest/v1/timing_heatmap?hour_cet=eq.{hour}&day_of_week=eq.{dow}',
                headers=HDR, timeout=15
            ).json()
            if existing:
                old = existing[0]
                new_count = old['sample_count'] + data['count']
                new_avg = ((old['avg_engagement'] * old['sample_count']) + (avg * data['count'])) / new_count
                requests.patch(
                    f'{SUPABASE_URL}/rest/v1/timing_heatmap?hour_cet=eq.{hour}&day_of_week=eq.{dow}',
                    headers={**HDR, 'Content-Type': 'application/json'},
                    json={'avg_engagement': round(new_avg, 2), 'sample_count': new_count},
                    timeout=15
                )
            else:
                requests.post(
                    f'{SUPABASE_URL}/rest/v1/timing_heatmap',
                    headers={**HDR, 'Content-Type': 'application/json'},
                    json={'hour_cet': hour, 'day_of_week': dow, 'avg_engagement': avg, 'sample_count': data['count']},
                    timeout=15
                )
        except Exception as e:
            print(f'  Error saving heatmap ({hour},{dow}): {e}')


def get_top_slots():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/timing_heatmap?order=avg_engagement.desc&limit=5',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f'Error fetching top slots: {e}')
        return []


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Timing Optimizer started...')

    posts = get_published_posts()
    print(f'Analyzing {len(posts)} published posts...')

    heatmap = build_heatmap(posts)
    save_heatmap(heatmap)

    top = get_top_slots()
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    print(f'\nEngagement heatmap data stored for {len(heatmap)} time slots.')

    if len(top) >= 3:
        print(f'\nTop 5 engagement time slots:')
        for slot in top[:5]:
            day = days[slot['day_of_week']] if slot['day_of_week'] < 7 else '?'
            print(f'  {day} {slot["hour_cet"]}:00 CET — engagement score {slot["avg_engagement"]}')
    else:
        print('\nNot enough data yet. Need more published posts.')

    print('Timing Optimizer done.')


if __name__ == '__main__':
    main()
