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
HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}


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


def fetch_hackernews():
    trends = []
    try:
        res = requests.get(
            'https://hacker-news.firebaseio.com/v0/topstories.json',
            timeout=15
        )
        res.raise_for_status()
        top_ids = res.json()[:15]
        for sid in top_ids:
            try:
                item = requests.get(
                    f'https://hacker-news.firebaseio.com/v0/item/{sid}.json',
                    timeout=15
                ).json()
                if item and item.get('title'):
                    trends.append({
                        'title': item['title'],
                        'url': item.get('url', f'https://news.ycombinator.com/item?id={sid}'),
                        'source': 'HackerNews',
                        'score': item.get('score', 0),
                    })
            except Exception:
                continue
    except Exception as e:
        print(f'  HN error: {e}')
    return trends


def fetch_reddit():
    trends = []
    subs = ['technology', 'artificial', 'MachineLearning']
    for sub in subs:
        try:
            res = requests.get(
                f'https://www.reddit.com/r/{sub}/hot.json?limit=5',
                headers={'User-Agent': 'NeuroPulse/1.0'},
                timeout=15
            )
            res.raise_for_status()
            for post in res.json()['data']['children']:
                data = post['data']
                trends.append({
                    'title': data['title'],
                    'url': data.get('url', f'https://reddit.com{data["permalink"]}'),
                    'source': f'r/{sub}',
                    'score': data.get('score', 0),
                })
        except Exception as e:
            print(f'  Reddit r/{sub} error: {e}')
        time.sleep(1)
    return trends


def fetch_google_trends():
    trends = []
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=60)
        pytrends.build_payload(kw_list=['AI', 'automation', 'SaaS'], timeframe='now 4-d')
        related = pytrends.related_queries()
        for kw in ['AI', 'automation', 'SaaS']:
            if kw in related and related[kw] is not None and 'top' in related[kw]:
                for _, row in related[kw]['top'].head(3).iterrows():
                    trends.append({
                        'title': row.get('query', ''),
                        'url': f'https://trends.google.com/trends/explore?q={row.get("query", "")}',
                        'source': 'Google Trends',
                        'score': int(row.get('value', 50)),
                    })
    except ImportError:
        print('  pytrends not installed. Skipping Google Trends.')
    except Exception as e:
        print(f'  Google Trends error: {e}')
    return trends


def score_trend(trend):
    prompt = f'''Score this trend for relevance to a tech content channel targeting EU professionals (DE, CH, AT, NL), age 25-40.

Title: {trend["title"]}
Source: {trend["source"]}
Score: {trend["score"]}

Criteria:
- Relevance to AI tools, SaaS, automation, developer productivity
- Timeliness and growth velocity
- Affiliate potential (Notion, Cursor, Zapier, Coursera, Udemy, DigitalOcean)

Reply JSON only:
{{"score": 1-10, "velocity": 1-10, "eu_angle": "hook for EU audience", "post_type": "news|tutorial|opinion"}}'''
    return call_mistral(prompt)


def save_trend_topic(trend, score_data):
    if score_data['score'] < 8:
        return False
    payload = {
        'title': trend['title'],
        'source_url': trend['url'],
        'eu_angle': score_data.get('eu_angle', ''),
        'post_type': score_data['post_type'],
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
        print(f'TREND HIJACKED (score {score_data["score"]}): {trend["title"][:60]}')
        return True
    except Exception as e:
        print(f'  Error saving trend: {e}')
        return False


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Trend Hijacker started...')

    all_trends = []
    print('Fetching HackerNews...')
    all_trends.extend(fetch_hackernews())
    time.sleep(1)

    print('Fetching Reddit...')
    all_trends.extend(fetch_reddit())

    print('Fetching Google Trends...')
    gt = fetch_google_trends()
    if gt:
        all_trends.extend(gt)

    print(f'Total trends collected: {len(all_trends)}')

    hijacked = 0
    for trend in all_trends:
        time.sleep(2)
        result = score_trend(trend)
        if result and result.get('score', 0) >= 8:
            if save_trend_topic(trend, result):
                hijacked += 1

    print(f'Trend Hijacker done. Fast-published {hijacked} high-scoring trends.')
    if hijacked > 0:
        print(f'  Next production cycle will generate content for these.')


if __name__ == '__main__':
    main()
