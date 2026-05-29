import os
import requests
import json
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
IG_SESSIONID = os.getenv('IG_SESSIONID')
IG_USERNAME = os.getenv('IG_USERNAME')

HDR = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}'
}

SHARED_VIDEO_PATH = os.path.join(os.environ.get('TEMP', '/tmp'), 'neuropulse_video.mp4')
CET = timezone(timedelta(hours=1))


def login_instagram():
    try:
        from instagrapi import Client
        cl = Client()

        if IG_SESSIONID:
            cl.set_settings({'cookies': {'sessionid': IG_SESSIONID}})
            cl.get_timeline_feed()
        elif IG_USERNAME and IG_PASSWORD:
            cl.login(IG_USERNAME, IG_PASSWORD)
        else:
            print('No Instagram credentials found.')
            return None

        cl.delay_range = [3, 6]
        user_id = cl.user_id_from_username(IG_USERNAME)
        print(f'Logged in as {IG_USERNAME} (id={user_id})')
        return cl
    except Exception as e:
        print(f'Login error: {e}')
        return None


def upload_to_supabase_storage(file_path, bucket='neuropulse-videos'):
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}'
    }

    filename = f'reel_{int(time.time())}.mp4'
    content_type = 'video/mp4'

    upload_url = f'{SUPABASE_URL}/storage/v1/object/{bucket}/{filename}'

    with open(file_path, 'rb') as f:
        resp = requests.post(
            upload_url,
            headers={**headers, 'Content-Type': content_type},
            data=f
        )

    if resp.status_code in (200, 201):
        public_url = f'{SUPABASE_URL}/storage/v1/object/public/{bucket}/{filename}'
        print(f'  Video uploaded to: {public_url}')
        return public_url
    else:
        print(f'  Storage upload failed: {resp.status_code} {resp.text}')
        return None


def publish_reel_graph_api(video_path, caption):
    """
    Instagram Graph API approach (requires FB Developer setup).
    Falls back to instagrapi if tokens not available.
    """
    ig_access_token = os.getenv('IG_ACCESS_TOKEN')
    ig_account_id = os.getenv('IG_ACCOUNT_ID')

    if ig_access_token and ig_account_id:
        video_url = upload_to_supabase_storage(video_path)
        if not video_url:
            return False

        print('Creating Reel container via Graph API...')
        r = requests.post(
            f'https://graph.facebook.com/v19.0/{ig_account_id}/media',
            params={
                'media_type': 'REELS',
                'video_url': video_url,
                'caption': caption,
                'share_to_feed': 'true',
                'access_token': ig_access_token
            }
        ).json()

        if 'id' not in r:
            print(f'  Container creation failed: {r}')
            return False

        container_id = r['id']
        print(f'  Container created: {container_id}. Waiting 35s for processing...')
        time.sleep(35)

        r2 = requests.post(
            f'https://graph.facebook.com/v19.0/{ig_account_id}/media_publish',
            params={
                'creation_id': container_id,
                'access_token': ig_access_token
            }
        ).json()

        if 'id' in r2:
            print(f'Reel published via Graph API! id={r2["id"]}')
            return True
        else:
            print(f'  Publish failed: {r2}')
            return False
    else:
        print('IG_ACCESS_TOKEN not configured, falling back to instagrapi...')
        return False


def publish_reel_instagrapi(video_path, caption):
    cl = login_instagram()
    if not cl:
        return False

    try:
        result = cl.clip_upload(video_path, caption)
        print(f'Reel published via instagrapi!')
        return True
    except Exception as e:
        print(f'  instagrapi Reel upload error: {e}')
        return False


def get_unpublished_posts():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.published&ig_published=eq.false&limit=1',
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
            json={'ig_published': True}, timeout=15
        )
    except Exception:
        pass


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Instagram Engine started...')

    if not os.path.exists(SHARED_VIDEO_PATH):
        print(f'No shared video found at {SHARED_VIDEO_PATH}. TikTok must run first.')
        return

    posts = get_unpublished_posts()
    if not posts:
        print('No unpublished posts for Instagram.')
        return

    post = posts[0]
    caption = post.get('instagram_caption') or post.get('title', '')
    print(f'Post: {post["title"][:50]}')

    success = publish_reel_graph_api(SHARED_VIDEO_PATH, caption)
    if not success:
        success = publish_reel_instagrapi(SHARED_VIDEO_PATH, caption)

    if success:
        mark_published(post['id'])
        print('Instagram Reel published!')
    else:
        print('Failed to publish Reel.')


if __name__ == '__main__':
    main()
