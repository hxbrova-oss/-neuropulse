import feedparser
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
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

CET = timezone(timedelta(hours=1))
HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}

TOOLS_RSS = [
    'https://www.artificialintelligence-news.com/feed/',
    'https://www.futuretools.io/feed',
]

AFFILIATE_PROGRAMS = {
    'notion': 'https://www.notion.so/affiliate-program',
    'cursor': 'https://cursor.sh/',
    'zapier': 'https://zapier.com/',
    'jasper': 'https://jasper.ai/',
    'midjourney': 'https://www.midjourney.com/',
}


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
                    'temperature': 0.7,
                    'max_tokens': 1024
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


def fetch_tool_items():
    items = []
    seen = set()
    for url in TOOLS_RSS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.title.strip()
                if title in seen:
                    continue
                seen.add(title)
                items.append({
                    'title': title,
                    'summary': entry.get('summary', '')[:500],
                    'link': entry.link,
                })
        except Exception as e:
            print(f'  RSS error ({url}): {e}')
        time.sleep(1)
    return items


def extract_tool(item):
    prompt = f'''Extract structured data about this AI tool:

Title: {item['title']}
Description: {item['summary'][:400]}

Reply JSON only:
{{
    "tool_name": "...",
    "one_line_description": "...",
    "category": "writing|image|video|coding|productivity|research|other",
    "pricing": "free|freemium|paid",
    "best_for": "developers|marketers|creators|everyone",
    "wow_factor": "the single most impressive thing about it",
    "affiliate_potential": true/false
}}'''
    return call_mistral(prompt)


def save_tool(tool_data):
    existing = requests.get(
        f'{SUPABASE_URL}/rest/v1/ai_tools_db?tool_name=eq.{tool_data["tool_name"]}&select=id',
        headers=HDR, timeout=15
    ).json()
    if existing:
        return False
    try:
        payload = {
            'tool_name': tool_data['tool_name'],
            'description': tool_data.get('one_line_description', ''),
            'category': tool_data.get('category', 'other'),
            'pricing': tool_data.get('pricing', ''),
            'best_for': tool_data.get('best_for', ''),
            'wow_factor': tool_data.get('wow_factor', ''),
            'affiliate_potential': tool_data.get('affiliate_potential', False),
        }
        for name, url in AFFILIATE_PROGRAMS.items():
            if name.lower() in tool_data['tool_name'].lower():
                payload['affiliate_url'] = url
                break
        requests.post(
            f'{SUPABASE_URL}/rest/v1/ai_tools_db',
            headers={**HDR, 'Content-Type': 'application/json'},
            json=payload, timeout=15
        )
        print(f'  New tool saved: {tool_data["tool_name"]}')
        return True
    except Exception as e:
        print(f'  Error saving tool: {e}')
        return False


def get_top_tools_this_week(limit=5):
    week_ago = (datetime.now(CET) - timedelta(days=7)).isoformat()
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/ai_tools_db?added_at=gte.{week_ago}&order=votes.desc&limit={limit}',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception:
        return []


def inject_affiliate_links(text, tools_list):
    for tool in tools_list:
        tool_lower = tool['tool_name'].lower()
        for prog_name, prog_url in AFFILIATE_PROGRAMS.items():
            if prog_name in tool_lower:
                placeholder = f'{{AFFILIATE_LINK_{tool_lower}}}'
                text = text.replace(placeholder, prog_url)
    return text


def generate_weekly_roundup():
    tools = get_top_tools_this_week(5)
    if not tools:
        print('No new tools this week for roundup.')
        return False

    prompt = f'''Write a high-engagement weekly roundup post for EU tech professionals (DE, CH, AT, NL), age 25-40.
Format: "5 AI Tools That Will Save You 10 Hours This Week"

Tools this week:
{json.dumps([{"name": t["tool_name"], "desc": t["description"], "cat": t["category"], "wow": t["wow_factor"]} for t in tools], indent=2)}

Write for ALL platforms:
1. TELEGRAM POST: detailed breakdown, one section per tool with emoji, strong CTA
2. INSTAGRAM CAPTION: punchy, visual-friendly, 20-25 hashtags
3. TIKTOK SCRIPT: "Number 5 will surprise you" style, fast-paced 45 seconds

Include affiliate placeholders like {{AFFILIATE_LINK_toolname}} where relevant.

Reply JSON only:
{{
  "telegram_post": "...",
  "instagram_caption": "...",
  "tiktok_script": "...",
  "hashtags": ["AITools", "Productivity"]
}}'''
    result = call_mistral(prompt)
    if not result:
        return False

    for field in ['telegram_post', 'instagram_caption', 'tiktok_script']:
        if result.get(field):
            result[field] = inject_affiliate_links(result[field], tools)

    try:
        tags = ' '.join(f'#{t}' for t in result.get('hashtags', []))
        text = f'{result["telegram_post"]}\n\n{tags}'
        requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json={'chat_id': CHANNEL_ID, 'text': text, 'parse_mode': 'HTML'},
            timeout=15
        ).raise_for_status()

        payload = {
            'title': f'Weekly Tools Roundup — {datetime.now(CET).strftime("%b %d")}',
            'status': 'published',
            'telegram_post': result['telegram_post'],
            'instagram_caption': result.get('instagram_caption', ''),
            'tiktok_script': result.get('tiktok_script', ''),
            'scoring': json.dumps(result.get('hashtags', [])),
            'published_at': datetime.now(CET).isoformat(),
        }
        requests.post(
            f'{SUPABASE_URL}/rest/v1/content_queue',
            headers={**HDR, 'Content-Type': 'application/json'},
            json=payload, timeout=15
        )
        print(f'Weekly roundup published to Telegram + queued for IG/TT.')
        return True
    except Exception as e:
        print(f'Error publishing roundup: {e}')
        return False


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Tools Database started...')

    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'collect'

    if mode == 'weekly':
        print('Generating weekly tools roundup...')
        generate_weekly_roundup()
        return

    print('Collecting new AI tools from RSS...')
    items = fetch_tool_items()
    print(f'Found {len(items)} potential tool mentions')

    new_count = 0
    for item in items:
        time.sleep(2)
        tool_data = extract_tool(item)
        if tool_data and tool_data.get('tool_name'):
            if save_tool(tool_data):
                new_count += 1

    total = requests.get(
        f'{SUPABASE_URL}/rest/v1/ai_tools_db?select=count',
        headers=HDR, timeout=15
    ).json()
    print(f'Tools Database: {new_count} new tools added. Total in DB: {len(total)}')
    print(f'  Weekly roundup ready for next Monday 8AM CET.')


if __name__ == '__main__':
    main()
