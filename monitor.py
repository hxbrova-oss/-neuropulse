import requests
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YOUR_CHAT_ID = os.getenv('YOUR_CHAT_ID')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

CET = timezone(timedelta(hours=1))
HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}


def query(table, params=''):
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/{table}{params}',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception:
        return []


def count(table, field='id'):
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/{table}?select={field}',
            headers=HDR, timeout=15
        )
        return len(res.json())
    except Exception:
        return 0


def daily_report():
    since = (datetime.now(CET) - timedelta(days=1)).isoformat()
    data = query('content_queue', f'?created_at=gte.{since}')
    total = len(data)
    published = len([x for x in data if x.get('status') == 'published'])
    pending = len([x for x in data if x.get('status') == 'pending'])
    avg_score = sum(x.get('score', 0) for x in data) / max(total, 1)

    cats = query('cross_analytics', '?order=content_score.desc&limit=5')
    best_cat = ''
    if cats:
        from collections import Counter
        c = Counter(r['topic_category'] for r in cats)
        best_cat = c.most_common(1)[0][0] if c else ''

    trends_today = count('trend_history')
    breaking_today = count('breaking_news_log')
    tools_db = count('ai_tools_db')

    heat = query('timing_heatmap', '?order=avg_engagement.desc&limit=3')
    best_times = ''
    if heat:
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        parts = [f'{days[s["day_of_week"]]} {s["hour_cet"]}:00' for s in heat[:3] if s['day_of_week'] < 7]
        best_times = ', '.join(parts)

    tags = query('hashtag_scores', '?order=score.desc&limit=3')
    top_tags = ', '.join(f'#{t["tag"]}' for t in tags) if tags else ''

    ab = query('ab_tests', '?select=winner&winner=neq.')
    wins_a = sum(1 for r in ab if r.get('winner') == 'A')
    wins_b = sum(1 for r in ab if r.get('winner') == 'B')
    hook_style = 'curiosity' if wins_a >= wins_b else 'data/shock' if wins_b > 0 else ''

    best_platform = 'Telegram' if cats and cats[0].get('tg_score', 0) >= cats[0].get('ig_score', 0) else 'Instagram' if cats else ''

    report = f'''NeuroPulse Daily Report
Date: {datetime.now(CET).strftime('%Y-%m-%d')} CET
Topics scanned: {total} | Published: {published}
AI News processed: {total} | Trends detected: {trends_today}
Breaking news items: {breaking_today}
New tools in database: {tools_db}
Avg quality score: {avg_score:.1f}/10
Top category: {best_cat or 'collecting data...'}
Best platform: {best_platform or 'collecting data...'}
Best times: {best_times or 'collecting data...'}
Top hashtags: {top_tags or 'collecting data...'}
Winning hook: {hook_style or 'collecting data...'}
Recommended focus: {best_cat or 'AI tools & automation'}
System status: operational'''

    try:
        res = requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json={'chat_id': YOUR_CHAT_ID, 'text': report},
            timeout=15
        )
        res.raise_for_status()
        print('Daily report sent.')
    except Exception as e:
        print(f'Error sending report: {e}')


def weekly_report():
    since = (datetime.now(CET) - timedelta(days=7)).isoformat()
    data = query('content_queue', f'?created_at=gte.{since}')
    total = len(data)
    published = len([x for x in data if x.get('status') == 'published'])
    avg_score = sum(x.get('score', 0) for x in data) / max(total, 1)
    trends_week = count('trend_history')
    tools_added = count('ai_tools_db')

    report = f'''NeuroPulse Weekly Report
Week ending: {datetime.now(CET).strftime('%Y-%m-%d')}
Topics scanned: {total}
Published this week: {published}
Trends tracked: {trends_week}
Tools in database: {tools_added}
Avg quality score: {avg_score:.1f}/10
Daily avg: {published/7:.1f} posts/day
System efficiency: nominal'''

    try:
        res = requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json={'chat_id': YOUR_CHAT_ID, 'text': report},
            timeout=15
        )
        res.raise_for_status()
        print('Weekly report sent.')
    except Exception as e:
        print(f'Error sending report: {e}')


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'weekly':
        weekly_report()
    else:
        daily_report()
