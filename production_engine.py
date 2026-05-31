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

HDR = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}'
}

ALEX_PERSONA = """
You are Alex — an AI engineer based in Berlin, 31 years old.
You've worked at 2 startups, you follow AI obsessively, and you have
strong opinions. You write for professionals in Central Europe who are
smart, busy, and allergic to hype.

YOUR VOICE:
- Direct. Never diplomatic when you can be honest.
- You have ONE clear take on every topic — not "on one hand, on the other"
- Dry humor occasionally. Never forced.
- You talk TO the reader, not AT them.
- You treat the reader as an equal — never explain obvious things.

YOUR WRITING RULES — these are absolute, never break them:
- NEVER start with a company name or product name
- NEVER use: "In a recent", "According to", "It is worth noting",
  "In conclusion", "Exciting", "Revolutionary", "Game-changer",
  "Groundbreaking", "Leverage", "Utilize", "Delve into"
- NEVER list features — make a point instead
- NEVER sound like a press release or a Wikipedia article
- NEVER use more than one exclamation mark per post
- ALWAYS open with something that makes the reader stop scrolling
- ALWAYS have one opinion or uncomfortable truth in every post
- ALWAYS write like you're texting a smart friend, not presenting to a board

BEFORE WRITING — answer these internally (don't include in output):
1. What does a busy professional in Frankfurt feel reading this headline?
2. What's the ONE thing worth knowing about this?
3. What's the uncomfortable truth or non-obvious angle?
4. Would Alex actually find this interesting? If not, why write about it?

Then write from THAT angle.
"""

WEEKLY_CONTENT_MIX = {
    "hot_take":       0.25,
    "tool_spotlight": 0.20,
    "explainer":      0.20,
    "industry_news":  0.15,
    "weekly_roundup": 0.10,
    "breaking":       0.10,
}

AFFILIATE_SOURCES = [
    'Notion (notion.so/product/notion-ai)',
    'Cursor AI (cursor.com)',
    'Zapier (zapier.com)',
    'Coursera (coursera.org)',
    'Udemy (udemy.com)',
    'DigitalOcean (digitalocean.com)',
]


def clean_json(raw):
    raw = re.sub(r'```json\s*', '', raw.strip())
    raw = re.sub(r'```\s*$', '', raw.strip())
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
    return raw

def fix_literal_newlines(text):
    """Replace literal newlines inside JSON string values with \\n."""
    def replace_in_string(m):
        content = m.group(0)
        content = content.replace('\n', '\\n')
        content = content.replace('\r', '\\r')
        return content
    # Match JSON string values: "..." with proper escaping
    pattern = r'"(?:[^"\\]|\\.)*"'
    return re.sub(pattern, replace_in_string, text)

def parse_json(text):
    for attempt_text in (text, clean_json(text)):
        try:
            result = json.loads(attempt_text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    fixed = fix_literal_newlines(clean_json(text))
    try:
        result = json.loads(fixed)
        if isinstance(result, dict):
            return result
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
                        result = json.loads(fixed[start:i+1])
                        if isinstance(result, dict):
                            return result
                    except:
                        pass
    return None

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
                    'temperature': 0.8,
                    'max_tokens': 2048
                },
                timeout=60
            )
            if res.status_code == 429:
                wait = (attempt + 1) * 10
                print(f'  Rate limited, waiting {wait}s...')
                time.sleep(wait)
                continue
            res.raise_for_status()
            text = res.json()['choices'][0]['message']['content']
            parsed = parse_json(text)
            if parsed is None:
                import tempfile as _tf
                dump_path = os.path.join(_tf.gettempdir(), f'mistral_dump_{int(time.time())}.txt')
                with open(dump_path, 'w', encoding='utf-8') as _f:
                    _f.write(text)
                print(f'  Parse failed, raw response dumped to {dump_path}')
            return parsed
        except Exception as e:
            print(f'  Mistral error (attempt {attempt+1}): {e}')
            time.sleep(5)
    return None


def get_pending():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.pending&order=score.desc&limit=3',
            headers=HDR,
            timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f'Error fetching pending topics: {e}')
        return []


def get_breaking_priority():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.pending&order=score.desc&limit=1',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        rows = res.json()
        if rows and rows[0].get('post_type') in ('model_launch', 'breaking'):
            return [rows[0]]
        return None
    except Exception:
        return None


def get_last_20_posts():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.published&order=published_at.desc&limit=20',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception:
        return []


def calculate_mix(posts):
    total = len(posts)
    if total == 0:
        return {}
    mix = {}
    for p in posts:
        pt = p.get('post_type', 'industry_news')
        mix[pt] = mix.get(pt, 0) + 1
    return {k: v / total for k, v in mix.items()}


def check_content_balance():
    posts = get_last_20_posts()
    actual_mix = calculate_mix(posts)
    underpublished = [
        k for k, v in WEEKLY_CONTENT_MIX.items()
        if actual_mix.get(k, 0) < v - 0.05
    ]
    return underpublished[0] if underpublished else None


def generate_post(topic):
    balance_type = check_content_balance()
    balance_hint = ''
    if balance_type:
        balance_hint = f'\nContent balance requires: "{balance_type}" type. Write from this angle if applicable.'

    prompt = f'''
{ALEX_PERSONA}

NEWS ITEM:
Title: {topic["title"]}
Source: {topic.get("source", "unknown")}
EU Angle: {topic.get("eu_angle", topic.get("arabic_angle", ""))}
Category: {topic.get("post_type", "news")}
{balance_hint}

Write posts for all platforms. Reply JSON only:
{{
    "telegram_post": "150-200 words. Alex's take. One strong opinion.
                      No bullet points unless absolutely necessary.
                      End with a question that makes people reply.",

    "instagram_caption": "Hook line (no hashtag, no emoji in first line —
                          this is what shows in preview, make it impossible
                          to ignore). Then 3-4 lines. Then CTA.
                          Hashtags at very end.",

    "tiktok_script": "45 seconds max. 120 words max.
                      First 3 words must be a hook — viewer decides
                      in 2 seconds. Fast. Punchy. One idea per sentence.
                      End: 'Follow — I post this stuff daily.'",

    "linkedin_post": "Professional but still Alex. Focus on career/business
                      impact. What does this mean for someone's job in 2025?
                      No motivational poster language.",

    "hook_variations": [
        "curiosity angle — makes reader feel they're missing something",
        "contrarian angle — challenges a common belief",
        "data/shock angle — a number or fact that surprises"
    ]
}}
'''

    # retry once if banned words slip in
    for attempt in range(2):
        result = call_mistral(prompt)
        if isinstance(result, list):
            result = result[0] if result else None
        if not isinstance(result, dict):
            print(f'  Attempt {attempt+1}: non-dict result ({type(result).__name__}), retrying...')
            continue
        banned = ['game-changer', 'groundbreaking', 'leverage', 'utilize', 'delve into', 'it is worth noting']
        has_banned = False
        for field in ('telegram_post', 'instagram_caption', 'tiktok_script'):
            text = result.get(field, '')
            if any(b in text.lower() for b in banned):
                print(f'  Banned word detected in {field}, regenerating...')
                time.sleep(2)
                has_banned = True
                break
        if has_banned:
            continue
        return result
    return result


def update_status(topic_id, post_data):
    try:
        payload = {
            'status': 'ready',
            'telegram_post': post_data['telegram_post'],
            'instagram_caption': post_data.get('instagram_caption', ''),
            'tiktok_script': post_data.get('tiktok_script', ''),
            'linkedin_post': post_data.get('linkedin_post', ''),
            'hashtags': json.dumps(post_data.get('hashtags', [])),
            'best_time': post_data.get('best_time', 'morning'),
        }
        res = requests.patch(
            f'{SUPABASE_URL}/rest/v1/content_queue?id=eq.{topic_id}',
            headers={**HDR, 'Content-Type': 'application/json'},
            json=payload,
            timeout=15
        )
        res.raise_for_status()
        return True
    except Exception as e:
        print(f'Error updating status: {e}')
        return False


def is_breaking(post):
    return post.get('post_type') in ('model_launch', 'breaking', 'news') and post.get('score', 0) >= 8


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Production Engine started...')

    breaking = get_breaking_priority()
    if breaking:
        print(f'Breaking priority topic found: {breaking[0]["title"][:60]}')
        pending = breaking
    else:
        pending = get_pending()
    print(f'Found {len(pending)} pending topics (3 sources: main + AI news + trends)')

    produced = 0
    for topic in pending:
        time.sleep(3)
        post_data = generate_post(topic)
        if post_data:
            # Breaking news: fast lane, tag it for video skip
            if is_breaking(topic):
                topic['post_type'] = 'breaking'
                post_data['post_type'] = 'breaking'
                if 'tiktok_script' in post_data:
                    del post_data['tiktok_script']
                if 'instagram_caption' in post_data:
                    del post_data['instagram_caption']
            if update_status(topic['id'], post_data):
                produced += 1
                print(f'Produced: {topic["title"][:60]}')
                if post_data.get('telegram_post'):
                    print(f'  Telegram preview: {post_data["telegram_post"][:100]}...')
                if post_data.get('tiktok_script'):
                    print(f'  TikTok script: {len(post_data["tiktok_script"])} chars')
                if post_data.get('instagram_caption'):
                    print(f'  Instagram caption: {len(post_data["instagram_caption"])} chars')
        else:
            print(f'Failed: {topic["title"][:60]}')

    print(f'Production done. Produced {produced} posts.')


if __name__ == '__main__':
    main()
