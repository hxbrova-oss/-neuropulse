import os, json, time, random, requests, re, shutil
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
MISTRAL_MODEL = os.getenv('MISTRAL_MODEL', 'mistral-large-latest')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
PEXELS_KEY = os.getenv('PEXELS_KEY', '')

CET = timezone(timedelta(hours=1))
HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}
_TMP = os.environ.get('TEMP', '/tmp')

FALLBACK_KEYWORDS = ['technology timelapse', 'data center', 'code screen', 'abstract tech', 'city night', 'server room', 'network animation', 'cinematic tech']

MUSIC_CACHE = {}


def clean_json(raw):
    raw = re.sub(r'```json\s*', '', raw.strip())
    raw = re.sub(r'```\s*$', '', raw.strip())
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
    return raw

def fix_literal_newlines(text):
    def _repl(m):
        c = m.group(0)
        return c.replace('\n', '\\n').replace('\r', '\\r')
    return re.sub(r'"(?:[^"\\]|\\.)*"', _repl, text)

def parse_json(text):
    for attempt in (text, clean_json(text)):
        try:
            r = json.loads(attempt)
            if isinstance(r, dict):
                return r
        except json.JSONDecodeError:
            pass
    fixed = fix_literal_newlines(clean_json(text))
    try:
        r = json.loads(fixed)
        if isinstance(r, dict):
            return r
    except json.JSONDecodeError:
        pass
    for delim in ('{', '['):
        start = fixed.find(delim)
        if start < 0:
            continue
        depth = 0
        for i in range(start, len(fixed)):
            if fixed[i] in ('{', '['):
                depth += 1
            elif fixed[i] in ('}', ']'):
                depth -= 1
                if depth == 0:
                    try:
                        r = json.loads(fixed[start:i+1])
                        if isinstance(r, dict):
                            return r
                    except:
                        pass
    return None

def call_mistral(prompt, retries=3, temp=0.7, max_tokens=2048):
    for attempt in range(retries):
        try:
            res = requests.post(
                'https://api.mistral.ai/v1/chat/completions',
                headers={'Authorization': f'Bearer {MISTRAL_API_KEY}', 'Content-Type': 'application/json'},
                json={'model': MISTRAL_MODEL, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': temp, 'max_tokens': max_tokens},
                timeout=60
            )
            if res.status_code == 429:
                time.sleep((attempt + 1) * 10)
                continue
            res.raise_for_status()
            text = res.json()['choices'][0]['message']['content']
            return parse_json(text)
        except Exception as e:
            print(f'  Mistral error (attempt {attempt+1}): {e}')
            time.sleep(5)
    return None


def generate_tts(script, output_path):
    try:
        try:
            import edge_tts
            import asyncio
            communicate = edge_tts.Communicate(script, voice='en-US-GuyNeural')
            asyncio.run(communicate.save(output_path))
            print(f'  TTS (edge): {os.path.getsize(output_path)} bytes')
            return True
        except Exception:
            from gtts import gTTS
            tts = gTTS(script, lang='en', slow=False)
            tts.save(output_path)
            print(f'  TTS (gTTS): {os.path.getsize(output_path)} bytes')
            return True
    except Exception as e:
        print(f'  TTS error: {e}')
        return False


def upload_to_supabase(file_path, bucket='neuropulse-videos'):
    try:
        filename = f'video_{int(time.time())}.mp4'
        with open(file_path, 'rb') as f:
            resp = requests.post(
                f'{SUPABASE_URL}/storage/v1/object/{bucket}/{filename}',
                headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'},
                files={'file': f}
            )
        if resp.status_code in (200, 201):
            url = f'{SUPABASE_URL}/storage/v1/object/public/{bucket}/{filename}'
            print(f'  Uploaded: {url}')
            return url
        return None
    except Exception as e:
        print(f'  Upload error: {e}')
        return None


def get_background_video(keyword, min_duration=30, timeout_sec=10):
    if not PEXELS_KEY:
        return None
    try:
        r = requests.get(
            f'https://api.pexels.com/videos/search?query={requests.utils.quote(keyword)}&per_page=8&min_duration={min_duration}',
            headers={'Authorization': PEXELS_KEY}, timeout=timeout_sec
        )
        if r.status_code != 200 or not r.json().get('videos'):
            kw = random.choice(FALLBACK_KEYWORDS)
            r = requests.get(
                f'https://api.pexels.com/videos/search?query={requests.utils.quote(kw)}&per_page=8',
                headers={'Authorization': PEXELS_KEY}, timeout=timeout_sec
            )
        data = r.json()
        if not data.get('videos'):
            return None
        videos = data['videos']
        video = random.choice(videos[:5])
        files = sorted(video['video_files'], key=lambda x: x.get('width', 0), reverse=True)
        hd = next((f for f in files if f.get('width', 0) <= 1080), files[0])
        path = os.path.join(_TMP, f'pexels_{int(time.time())}_{random.randint(100,999)}.mp4')
        r2 = requests.get(hd['link'], stream=True, timeout=timeout_sec)
        with open(path, 'wb') as f:
            for chunk in r2.iter_content(8192):
                if chunk:
                    f.write(chunk)
        sz = os.path.getsize(path)
        if sz < 10000:
            os.remove(path)
            return None
        print(f'  Pexels background: {hd["width"]}x{hd.get("height", 0)}, {sz} bytes')
        return path
    except Exception as e:
        print(f'  Pexels error: {e}')
        return None


def download_music(mood='upbeat'):
    mood_key = mood if mood in ('tense', 'upbeat', 'dark', 'inspiring', 'curious') else 'upbeat'
    if mood_key in MUSIC_CACHE and os.path.exists(MUSIC_CACHE[mood_key]):
        return MUSIC_CACHE[mood_key]

    UPBEAT = 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'
    TENSE = 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3'
    DARK = 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3'
    INSPIRING = 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3'
    CURIOUS = 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3'

    urls = {'upbeat': UPBEAT, 'tense': TENSE, 'dark': DARK, 'inspiring': INSPIRING, 'curious': CURIOUS}
    url = urls.get(mood_key, UPBEAT)

    try:
        path = os.path.join(_TMP, f'music_{mood_key}.mp3')
        if os.path.exists(path):
            MUSIC_CACHE[mood_key] = path
            return path
        r = requests.get(url, timeout=15)
        with open(path, 'wb') as f:
            f.write(r.content)
        MUSIC_CACHE[mood_key] = path
        print(f'  Music downloaded: {mood_key} ({os.path.getsize(path)} bytes)')
        return path
    except Exception as e:
        print(f'  Music download error: {e}')
        return None


def plan_shots(script, topic_category='news'):
    prompt = f'''You are a TikTok/Reels video director.
Script: "{script}"
Category: {topic_category}

Break this into exactly 5 shots for a 45-second video.
Each shot is 3-4 seconds long and visually represents one idea.

Rules:
- Shot 1 (0-3s): HOOK — most visually striking
- Shot 2-4 (3-35s): core content — one idea per shot
- Shot 5 (35-45s): CTA — clean, direct

For each shot:
- "keyword": a Pexels video search term (2-3 words) for background footage (e.g. "abstract data flow", "server room neon", "city night timelapse")
- "text_overlay": 2-4 words max shown on screen during this shot
- "transition_out": "fade" or "slide_left" or "zoom" or "cut"
- "duration": 3-5 seconds

Reply JSON only:
{{
    "shots": [
        {{
            "shot_number": 1,
            "duration": 3,
            "keyword": "search term for Pexels",
            "text_overlay": "text on screen",
            "transition_out": "fade|slide_left|zoom|cut"
        }}
    ],
    "music_mood": "tense|upbeat|dark|inspiring|curious",
    "total_duration_guess": 45
}}'''
    return call_mistral(prompt, temp=0.8)


def render_text_overlay(text, font_size=68, shadow_offset=3, width=1080, height=400):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('arial.ttf', font_size)
    except Exception:
        font = ImageFont.load_default()

    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    x = (width - tw) // 2
    y = (height - th) // 2
    draw.text((x + shadow_offset, y + shadow_offset), text, fill=(0, 0, 0, 180), font=font)
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    path = os.path.join(_TMP, f'overlay_{int(time.time())}_{random.randint(100,999)}.png')
    img.save(path)
    return path


def render_branding():
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGBA', (220, 50), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('arial.ttf', 28)
    except Exception:
        font = ImageFont.load_default()
    draw.text((1, 1), 'NeuroPulse', fill=(0, 0, 0, 100), font=font)
    draw.text((0, 0), 'NeuroPulse', fill=(0, 212, 255, 200), font=font)
    path = os.path.join(_TMP, f'brand_{int(time.time())}.png')
    img.save(path)
    return path


def make_progress_bar(duration, total_width=1080, height=6, color=(0, 212, 255)):
    import numpy as np
    def progress_frame(t):
        p = int((t / duration) * total_width)
        frame = np.zeros((height, total_width, 3), dtype='uint8')
        frame[:, :p] = color
        return frame
    return progress_frame


def produce_video(topic):
    import asyncio as _asyncio
    from moviepy import (
        AudioFileClip, VideoFileClip, ColorClip, CompositeVideoClip,
        ImageClip, VideoClip, concatenate_videoclips, concatenate_audioclips
    )
    print(f'--- Producing video: {topic["title"][:50]} ---')

    script = topic.get('tiktok_script', '')
    if not script:
        print('No tiktok_script, cannot produce video')
        return None

    audio_path = os.path.join(_TMP, 'tt_audio.mp3')
    output_path = os.path.join(_TMP, 'neuropulse_video.mp4')

    if not generate_tts(script, audio_path):
        return None

    audio = AudioFileClip(audio_path)
    dur = audio.duration
    print(f'  Audio duration: {dur:.1f}s')

    shot_plan = plan_shots(script, topic.get('post_type', 'news'))
    shots = shot_plan['shots'] if shot_plan and shot_plan.get('shots') else []

    if not shots:
        print('  No shot plan, using script_lines directly')
        lines = [l.strip() for l in script.split('\n') if l.strip()]
        words_per_shot = max(1, len(lines) // 5)
        shots = []
        for i in range(0, len(lines), words_per_shot):
            group = lines[i:i+words_per_shot]
            kw = random.choice(FALLBACK_KEYWORDS)
            shots.append({
                'keyword': kw,
                'text_overlay': group[0][:20] if group else '',
                'duration': 5,
                'transition_out': 'fade',
            })

    total_planned = sum(s.get('duration', 5) for s in shots)
    scale = dur / total_planned if total_planned > 0 else 1

    music_mood = shot_plan.get('music_mood', 'upbeat') if shot_plan else 'upbeat'

    print(f'  Downloading {len(shots)} Pexels backgrounds...')
    bg_paths = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        fut_to_idx = {ex.submit(get_background_video, s['keyword'], min_duration=int(s.get('duration', 5))): i for i, s in enumerate(shots)}
        results = {}
        for f in as_completed(fut_to_idx):
            idx = fut_to_idx[f]
            path = f.result()
            if path:
                results[idx] = path
    bg_paths = [results.get(i) for i in range(len(shots))]

    music_path = download_music(music_mood)
    brand_img = render_branding()

    clip_layers = []
    current_time = 0
    opacities = {'fade': 0.6, 'slide_left': 0.5, 'zoom': 0.55, 'cut': 0.6}
    transitions = {'fade': 'fade', 'slide_left': 'slide', 'zoom': 'zoom', 'cut': 'cut'}

    for i, shot in enumerate(shots):
        s_dur = min(shot.get('duration', 5) * scale, dur - current_time)
        if s_dur <= 0.5:
            break

        bg = bg_paths[i]
        trans_out = shot.get('transition_out', 'fade')
        opacity = opacities.get(trans_out, 0.6)

        if bg and os.path.getsize(bg) > 10000:
            try:
                bg_clip = VideoFileClip(bg).subclipped(0, min(s_dur, 60)).resized((1080, 1920))
                overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=s_dur).with_opacity(opacity)
                shot_clip = CompositeVideoClip([bg_clip, overlay]).with_start(current_time)
            except Exception as e:
                print(f'  BG error shot {i}: {e}')
                shot_clip = ColorClip(size=(1080, 1920), color=(10, 15, 30), duration=s_dur).with_start(current_time)
        else:
            shot_clip = ColorClip(size=(1080, 1920), color=(10, 15, 30), duration=s_dur).with_start(current_time)

        clip_layers.append(shot_clip)

        overlay_text = shot.get('text_overlay', '')
        if overlay_text:
            overlay_img = render_text_overlay(overlay_text)
            text_clip = (ImageClip(overlay_img)
                        .with_start(current_time)
                        .with_duration(s_dur)
                        .with_position(('center', 750)))
            clip_layers.append(text_clip)

        current_time += s_dur

    actual_dur = min(current_time, dur)

    progress_func = make_progress_bar(actual_dur)
    progress_clip = VideoClip(progress_func, duration=actual_dur).with_position(('center', 1914))

    brand_clip = ImageClip(brand_img).with_duration(actual_dur).with_position((860, 60)).with_opacity(0.8)

    clip_layers.append(progress_clip)
    clip_layers.append(brand_clip)

    final = CompositeVideoClip(clip_layers, size=(1080, 1920))

    if music_path:
        try:
            music = AudioFileClip(music_path).with_duration(actual_dur)
            music = music.with_effects([lambda t, v: v * max(0, 1 - t/actual_dur * 0.5)])
            music = music.with_volume_scaled(0.08)
            final = final.with_audio(CompositeVideoClip([final.with_audio(audio), ColorClip(size=(1,1), color=(0,0,0), duration=1).with_audio(music)]).audio)
        except Exception as e:
            print(f'  Music mix error: {e}')
            final = final.with_audio(audio)
    else:
        final = final.with_audio(audio)

    print(f'  Rendering {actual_dur:.1f}s video...')
    final.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', threads=4, logger=None)
    audio.close()

    for p in bg_paths:
        if p: os.remove(p)
    for p in clip_layers:
        if isinstance(p, ImageClip) and p.filename:
            try: os.remove(p.filename)
            except: pass

    print(f'  Video produced: {os.path.getsize(output_path)} bytes')
    return output_path


def get_unpublished_videos():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.ready&order=score.desc&limit=1',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f'Error: {e}')
        return []


def mark_video_ready(post_id, video_url):
    try:
        requests.patch(
            f'{SUPABASE_URL}/rest/v1/content_queue?id=eq.{post_id}',
            headers={**HDR, 'Content-Type': 'application/json'},
            json={'video_url': video_url, 'status': 'published'}, timeout=15
        )
    except Exception:
        pass


def clean_old_audio():
    try:
        os.remove(os.path.join(_TMP, 'tt_audio.mp3'))
    except Exception:
        pass


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Video Producer started...')

    posts = get_unpublished_videos()
    if not posts:
        print('No pending videos.')
        return

    for post in posts:
        video_path = produce_video(post)
        if video_path:
            video_url = upload_to_supabase(video_path)
            if video_url:
                mark_video_ready(post['id'], video_url)
                print(f'  Video ready and linked to post {post["id"]}')
                shutil.copy2(video_path, os.path.join(_TMP, 'neuropulse_video.mp4'))
            else:
                print('  Failed to upload video')
        else:
            print(f'  Video production failed for post {post["id"]}')
        clean_old_audio()

    print('Video Producer done.')


if __name__ == '__main__':
    main()
