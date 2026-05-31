import os, json, time, random, asyncio, requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

CET = timezone(timedelta(hours=1))
HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}
SHARED_VIDEO_PATH = os.path.join(os.environ.get('TEMP', '/tmp'), 'neuropulse_video.mp4')


def is_breaking_news(post):
    pt = post.get('post_type', '')
    return pt == 'breaking' or (pt == 'news' and post.get('score', 0) >= 8)


def upload_to_tiktok(video_path, description):
    try:
        from tiktok_uploader.upload import upload_video
        cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tiktok_cookies.txt')
        if not os.path.exists(cookies_path):
            print(f'  Cookies not found: {cookies_path}')
            return False
        print('  Uploading to TikTok...')
        upload_video(video_path, description=description, cookies=cookies_path)
        print('  TikTok upload completed!')
        return True
    except ImportError:
        print('  tiktok-uploader not installed.')
        return False
    except Exception as e:
        print(f'  TikTok upload error: {e}')
        return False


def get_unpublished_posts():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.published&tt_published=eq.false&limit=1',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f'Error fetching posts: {e}')
        return []


def mark_published(post_id):
    try:
        requests.patch(
            f'{SUPABASE_URL}/rest/v1/content_queue?id=eq.{post_id}',
            headers={**HDR, 'Content-Type': 'application/json'},
            json={'tt_published': True}, timeout=15
        )
    except Exception:
        pass


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] TikTok Engine started...')

    posts = get_unpublished_posts()
    if not posts:
        print('No unpublished posts for TikTok.')
        return

    post = posts[0]
    print(f'Processing: {post["title"][:50]}')

    if is_breaking_news(post):
        print('  Breaking news — skipping video (TG only)')
        mark_published(post['id'])
        print('  Marked TT published (skip)')
        return

    if not os.path.exists(SHARED_VIDEO_PATH):
        print(f'  No video file at {SHARED_VIDEO_PATH}. Run video_producer.py first.')
        return

    description = post.get('telegram_post', post.get('title', ''))[:300]
    if upload_to_tiktok(SHARED_VIDEO_PATH, description):
        mark_published(post['id'])
        print('TikTok video published!')
    else:
        print('TikTok upload failed. Video exists at:', SHARED_VIDEO_PATH)

    print('TikTok Engine done.')


if __name__ == '__main__':
    main()
