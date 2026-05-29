import os
import json
import time
import asyncio
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

CET = timezone(timedelta(hours=1))

HDR = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}'
}

SHARED_VIDEO_PATH = os.path.join(os.environ.get('TEMP', '/tmp'), 'neuropulse_video.mp4')


def generate_tts(script, output_path):
    try:
        import edge_tts
        communicate = edge_tts.Communicate(script, voice='en-US-GuyNeural')
        asyncio.run(communicate.save(output_path))
        print(f'  TTS generated: {os.path.getsize(output_path)} bytes')
        return True
    except Exception as e:
        print(f'  TTS error: {e}')
        return False


def create_video(script_lines, audio_path, output_path):
    try:
        from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, TextClip
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        bg = ColorClip(size=(1080, 1920), color=(10, 15, 30), duration=duration)
        clips = [bg]
        y_start = 700
        for i, line in enumerate(script_lines):
            txt = TextClip(
                text=line,
                font_size=65,
                color='white',
                font='Arial-Bold',
                size=(900, None),
                method='caption'
            )
            start_time = i * (duration / len(script_lines))
            txt = txt.with_start(start_time).with_duration(duration / len(script_lines))
            txt = txt.with_position(('center', y_start + (i % 3) * 150))
            clips.append(txt)
        video = CompositeVideoClip(clips).with_audio(audio)
        video.write_videofile(
            output_path, fps=30, codec='libx264',
            audio_codec='aac', logger=None
        )
        audio.close()
        print(f'  Video created: {os.path.getsize(output_path)} bytes')
        return True
    except Exception as e:
        print(f'  Video error: {e}')
        return False


def upload_to_tiktok(video_path, description):
    try:
        from tiktok_uploader.upload import upload_video
        cookies_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'tiktok_cookies.txt'
        )
        if not os.path.exists(cookies_path):
            print(f'  Cookies file not found: {cookies_path}')
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

    script = post.get('tiktok_script', '')
    if not script:
        print('No tiktok_script found.')
        return

    script_lines = [l.strip() for l in script.split('\n') if l.strip()]
    print(f'  Script: {len(script_lines)} lines')

    temp_dir = os.environ.get('TEMP', '/tmp')
    audio_path = os.path.join(temp_dir, 'tt_audio.mp3')

    print('Generating TTS audio...')
    if not generate_tts(script, audio_path):
        return

    print('Creating video...')
    if not create_video(script_lines, audio_path, SHARED_VIDEO_PATH):
        return

    description = post.get('telegram_post', post.get('title', ''))[:300]
    if upload_to_tiktok(SHARED_VIDEO_PATH, description):
        mark_published(post['id'])
        print(f'TikTok video published!')

    try:
        os.remove(audio_path)
    except Exception:
        pass

    print('TikTok Engine done. Video saved at:', SHARED_VIDEO_PATH)


if __name__ == '__main__':
    import requests
    main()
