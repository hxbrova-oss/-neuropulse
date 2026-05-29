import requests
import json
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

CET = timezone(timedelta(hours=1))

HDR = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}'
}


def get_ready_posts():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.ready&order=score.desc&limit=1',
            headers=HDR,
            timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f'Error fetching ready posts: {e}')
        return []


def publish(text, hashtags):
    tags = ' '.join([f'#{t}' for t in hashtags])
    full_text = f'{text}\n\n{tags}'

    try:
        res = requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json={
                'chat_id': CHANNEL_ID,
                'text': full_text,
                'parse_mode': 'HTML'
            },
            timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f'Error publishing to Telegram: {e}')
        return {'ok': False}


def mark_published(post_id):
    try:
        res = requests.patch(
            f'{SUPABASE_URL}/rest/v1/content_queue?id=eq.{post_id}',
            headers={**HDR, 'Content-Type': 'application/json'},
            json={
                'status': 'published',
                'published_at': datetime.now(CET).isoformat()
            },
            timeout=15
        )
        res.raise_for_status()
        return True
    except Exception as e:
        print(f'Error marking as published: {e}')
        return False


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Publishing Engine started...')

    posts = get_ready_posts()

    if not posts:
        print('No ready posts to publish. Skipping.')
        return

    post = posts[0]
    try:
        hashtags = json.loads(post.get('hashtags', '[]'))
    except json.JSONDecodeError:
        hashtags = []

    result = publish(post['telegram_post'], hashtags)
    if result.get('ok'):
        mark_published(post['id'])
        print(f'Published: {post["title"][:60]}')
    else:
        print(f'Failed to publish: {post["title"][:60]}')

    print('Publishing done.')


if __name__ == '__main__':
    main()
