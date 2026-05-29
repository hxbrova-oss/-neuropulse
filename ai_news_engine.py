import feedparser
import requests
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
MISTRAL_MODEL = os.getenv('MISTRAL_MODEL', 'mistral-large-latest')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

CET = timezone(timedelta(hours=1))
HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}

AI_SOURCES = {
    'arxiv': 'http://export.arxiv.org/rss/cs.AI',
    'arxiv_lg': 'http://export.arxiv.org/rss/cs.LG',
    'huggingface': 'https://huggingface.co/blog/feed.xml',
    'ai_news': 'https://www.artificialintelligence-news.com/feed/',
    'mit_ai': 'https://news.mit.edu/rss/topic/artificial-intelligence',
    'deepmind': 'https://deepmind.google/blog/rss.xml',
    'openai_news': 'https://openai.com/blog/rss.xml',
    'anthropic': 'https://www.anthropic.com/rss.xml',
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


def fetch_rss_feeds():
    items = []
    seen = set()
    for name, url in AI_SOURCES.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title = entry.title.strip()
                if title in seen:
                    continue
                seen.add(title)
                items.append({
                    'title': title,
                    'summary': entry.get('summary', '')[:500],
                    'link': entry.link,
                    'source': name,
                    'published': entry.get('published', '')
                })
        except Exception as e:
            print(f'  RSS error ({name}): {e}')
        time.sleep(1)
    return items


def score_ai_item(item):
    prompt = f'''Score this AI news item 1-10 for an EU tech professional audience (DE, CH, AT, NL), age 25-40.

Title: {item['title']}
Source: {item['source']}
Summary: {item['summary'][:300]}

Scoring criteria:
- Is this a NEW model/tool launch? (+3 points)
- Does it affect developers/professionals directly? (+2 points)
- From a major lab (OpenAI/Anthropic/Google/Meta)? (+2 points)
- Breaking news / first 24 hours? (+2 points)
- Has viral potential? (+1 point)

Reply JSON only:
{{"score": 1-10, "category": "model_launch|tool|research|industry_news",
  "urgency": "breaking|normal", "hook": "one provocative sentence",
  "eu_angle": "hook for EU audience"}}'''
    return call_mistral(prompt)


def breaking_fast_lane(item, score_data):
    print(f'  BREAKING NEWS FAST LANE: {item["title"][:60]}')
    payload = {
        'title': item['title'],
        'source_url': item['link'],
        'eu_angle': score_data.get('eu_angle', score_data.get('hook', '')),
        'post_type': score_data.get('category', 'news'),
        'score': 10,
        'status': 'pending',
        'created_at': datetime.now(CET).isoformat()
    }
    try:
        requests.post(
            f'{SUPABASE_URL}/rest/v1/content_queue',
            headers={**HDR, 'Content-Type': 'application/json'},
            json=payload, timeout=15
        ).raise_for_status()
        log = {
            'title': item['title'],
            'source': item['source'],
            'platforms_published': 'queue',
        }
        requests.post(
            f'{SUPABASE_URL}/rest/v1/breaking_news_log',
            headers={**HDR, 'Content-Type': 'application/json'},
            json=log, timeout=15
        )
        print(f'  Urgency: breaking — queued for immediate production')
    except Exception as e:
        print(f'  Error fast-lane: {e}')


def save_ai_topic(item, score_data):
    payload = {
        'title': item['title'],
        'source_url': item['link'],
        'eu_angle': score_data.get('eu_angle', score_data.get('hook', '')),
        'post_type': score_data.get('category', 'news'),
        'score': score_data['score'],
        'status': 'pending',
        'created_at': datetime.now(CET).isoformat()
    }
    try:
        res = requests.post(
            f'{SUPABASE_URL}/rest/v1/content_queue',
            headers={**HDR, 'Content-Type': 'application/json'},
            json=payload, timeout=15
        )
        res.raise_for_status()
        print(f'  Saved (score {score_data["score"]}): {item["title"][:60]}')
        return True
    except Exception as e:
        print(f'  Error saving: {e}')
        return False


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] AI News Engine started...')

    items = fetch_rss_feeds()
    print(f'Fetched {len(items)} AI news items from {len(AI_SOURCES)} sources')

    breaking_count = 0
    saved = 0
    for item in items:
        time.sleep(2)
        result = score_ai_item(item)
        if not result:
            continue
        score = result.get('score', 0)
        urgency = result.get('urgency', 'normal')
        if urgency == 'breaking' and score >= 8:
            breaking_fast_lane(item, result)
            breaking_count += 1
        elif score >= 7:
            if save_ai_topic(item, result):
                saved += 1
        else:
            print(f'  Skipped (score {score}): {item["title"][:50]}')

    print(f'\nAI News Engine done. Breaking: {breaking_count}, Queued: {saved}')
    if breaking_count > 0:
        print(f'  Next production cycle will process breaking topics first.')


if __name__ == '__main__':
    main()
