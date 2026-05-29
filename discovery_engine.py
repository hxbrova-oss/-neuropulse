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

CET = timezone(timedelta(hours=1))

RSS_FEEDS = [
    'https://feeds.feedburner.com/TechCrunch',
    'https://venturebeat.com/category/ai/feed/',
    'https://www.theverge.com/rss/index.xml',
    'https://hnrss.org/frontpage',
    'https://tldr.tech/api/rss/tech',
]


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
                wait = (attempt + 1) * 10
                print(f'  Rate limited, waiting {wait}s...')
                time.sleep(wait)
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


def fetch_trending_topics():
    topics = []
    seen_titles = set()
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                title = entry.title.strip()
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                topics.append({
                    'title': title,
                    'summary': entry.get('summary', '')[:500],
                    'link': entry.link,
                    'source': feed.feed.title,
                })
        except Exception as e:
            print(f'Error fetching {url}: {e}')
            continue
    return topics


def score_topic(topic):
    prompt = f'''You are a content strategist for a tech-focused Telegram channel targeting English-speaking professionals in Central Europe (Germany, Switzerland, Austria, Netherlands).

Score this topic from 1-10 for relevance and monetization potential.

Title: {topic["title"]}
Summary: {topic["summary"]}

Scoring criteria:
- Relevance to AI tools, automation, SaaS, developer productivity
- Appeal to tech professionals aged 25-40 in EU
- Affiliate potential (Notion, Cursor, Zapier, Coursera, Udemy, DigitalOcean)
- Timeliness and urgency

Reply with JSON only, no extra text:
{{"score": N, "eu_angle": "The specific EU professional angle or hook", "post_type": "news|tutorial|opinion"}}'''
    return call_mistral(prompt)


def save_topic(topic, score_data):
    if score_data['score'] < 7:
        print(f'Skipped (score {score_data["score"]}): {topic["title"][:60]}')
        return False

    payload = {
        'title': topic['title'],
        'source_url': topic['link'],
        'arabic_angle': score_data.get('eu_angle', score_data.get('arabic_angle', '')),
        'post_type': score_data['post_type'],
        'score': score_data['score'],
        'status': 'pending',
        'created_at': datetime.now(CET).isoformat()
    }

    try:
        res = requests.post(
            f'{SUPABASE_URL}/rest/v1/content_queue',
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=15
        )
        res.raise_for_status()
        print(f'Saved (score {score_data["score"]}): {topic["title"][:60]}')
        return True
    except Exception as e:
        print(f'Error saving topic: {e}')
        return False


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Discovery Engine started...')

    topics = fetch_trending_topics()
    print(f'Found {len(topics)} unique topics from RSS feeds')

    saved = 0
    for topic in topics:
        time.sleep(2)
        score_data = score_topic(topic)
        if score_data:
            if save_topic(topic, score_data):
                saved += 1
        else:
            print(f'Failed to score: {topic["title"][:60]}')

    print(f'Discovery done. Saved {saved} topics to Supabase.')


if __name__ == '__main__':
    main()
