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

TWITTER_BEARER = os.getenv('TWITTER_BEARER_TOKEN', '')
TIKTOK_RESEARCH_TOKEN = os.getenv('TIKTOK_RESEARCH_TOKEN', '')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
PH_TOKEN = os.getenv('PH_TOKEN', '')

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


def get_previous_volume(trend_name):
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/trend_history?trend_name=eq.{quote(trend_name)}&order=recorded_at.desc&limit=1',
            headers=HDR, timeout=15
        ).json()
        if res:
            return res[0].get('volume', 0)
    except Exception:
        pass
    return None


def save_trend_history(trend_name, source, volume, velocity):
    try:
        payload = {
            'trend_name': trend_name,
            'source': source,
            'volume': volume,
            'velocity': round(velocity, 1)
        }
        requests.post(
            f'{SUPABASE_URL}/rest/v1/trend_history',
            headers={**HDR, 'Content-Type': 'application/json'},
            json=payload, timeout=15
        )
    except Exception as e:
        print(f'  Error saving trend history: {e}')


def fetch_twitter_trends():
    trends = []
    if not TWITTER_BEARER:
        print('  Twitter: no bearer token, skipping.')
        return trends
    try:
        import tweepy
        client = tweepy.Client(bearer_token=TWITTER_BEARER)
        query = '(AI OR artificial intelligence OR machine learning OR SaaS OR automation) lang:en -is:retweet'
        result = client.search_recent_tweets(query=query, max_results=10, tweet_fields=['public_metrics'])
        if result.data:
            for tweet in result.data:
                metrics = tweet.public_metrics or {}
                likes = metrics.get('like_count', 0)
                rt = metrics.get('retweet_count', 0)
                score = likes + rt
                if score > 50:
                    trends.append({
                        'name': tweet.text[:100],
                        'volume': score,
                        'source': 'twitter'
                    })
        print(f'  Twitter: {len(trends)} popular tweets about AI/tech')
    except ImportError:
        print('  Twitter: tweepy not installed.')
    except Exception as e:
        print(f'  Twitter error: {e}')
    return trends


def fetch_youtube_trends():
    trends = []
    if not YOUTUBE_API_KEY:
        print('  YouTube: no API key, skipping.')
        return trends
    try:
        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY, cache_discovery=False)
        r = youtube.videos().list(
            part='snippet,statistics',
            chart='mostPopular',
            regionCode='DE',
            videoCategoryId='28',
            maxResults=10
        ).execute()
        for v in r.get('items', []):
            views = int(v['statistics'].get('viewCount', 0))
            if views > 100000:
                trends.append({
                    'name': v['snippet']['title'],
                    'volume': views,
                    'source': 'youtube',
                    'channel': v['snippet']['channelTitle']
                })
        print(f'  YouTube: {len(trends)} tech videos >100k views')
    except ImportError:
        print('  YouTube: googleapiclient not installed.')
    except Exception as e:
        print(f'  YouTube error: {e}')
    return trends


def fetch_producthunt_trends():
    trends = []
    if not PH_TOKEN:
        print('  Product Hunt: no token, skipping.')
        return trends
    try:
        query = """
        { posts(first: 10, order: VOTES) {
            edges { node {
                name tagline votesCount
                topics { edges { node { name } } }
            }}
        }}
        """
        r = requests.post(
            'https://api.producthunt.com/v2/api/graphql',
            headers={
                'Authorization': f'Bearer {PH_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={'query': query},
            timeout=15
        )
        if r.status_code != 200:
            print(f'  Product Hunt API error: {r.status_code} — check token')
            return trends
        data = r.json()
        if 'errors' in data:
            print(f'  Product Hunt auth error: {data["errors"][0].get("error_description", "invalid token")}')
            return trends
        for p in data.get('data', {}).get('posts', {}).get('edges', []):
            node = p['node']
            if node['votesCount'] > 100:
                trends.append({
                    'name': node['name'],
                    'tagline': node['tagline'],
                    'volume': node['votesCount'],
                    'source': 'producthunt'
                })
        print(f'  Product Hunt: {len(trends)} products >100 votes')
    except ImportError:
        print('  Product Hunt: requests not available.')
    except Exception as e:
        print(f'  Product Hunt error: {e}')
    return trends


def fetch_tiktok_trends():
    trends = []
    if not TIKTOK_RESEARCH_TOKEN:
        print('  TikTok: no research token, skipping.')
        return trends
    try:
        today = datetime.now().strftime('%Y%m%d')
        r = requests.post(
            'https://open.tiktokapis.com/v2/research/video/query/',
            headers={'Authorization': f'Bearer {TIKTOK_RESEARCH_TOKEN}'},
            json={
                'query': {
                    'and': [{'field': 'hashtag_name', 'operation': 'IN',
                             'field_values': ['AItools', 'artificialintelligence']}]
                },
                'start_date': '20240101',
                'end_date': today,
                'max_count': 10,
                'fields': 'music_id,like_count,share_count'
            },
            timeout=15
        ).json()
        music_ids = [v.get('music_id') for v in r.get('data', {}).get('videos', []) if v.get('music_id')]
        if music_ids:
            from collections import Counter
            top_music = Counter(music_ids).most_common(1)[0][0]
            trends.append({
                'name': f'trending_sound:{top_music}',
                'volume': len(music_ids) * 1000,
                'source': 'tiktok',
                'music_id': top_music
            })
        print(f'  TikTok: {len(trends)} trending sounds')
    except Exception as e:
        print(f'  TikTok error: {e}')
    return trends


def calculate_velocity(trend_name, current_volume):
    prev = get_previous_volume(trend_name)
    if prev and prev > 0:
        return (current_volume - prev) / prev * 100
    return 0


def score_trend(trend, velocity):
    prompt = f'''Score this trend for relevance to EU tech professionals (DE, CH, AT, NL), age 25-40.

Name: {trend.get("name", trend.get("tagline", ""))}
Source: {trend.get("source", "unknown")}
Volume: {trend.get("volume", 0)}
Velocity: {velocity:.1f}% growth in 3h

Criteria:
- Relevance to AI tools, SaaS, automation, developer productivity
- Timeliness (velocity > 50% = urgent)
- Volume (higher = broader appeal)
- Affiliate potential (Notion, Cursor, Zapier, Coursera, Udemy, DigitalOcean)

Reply JSON only:
{{"relevance": 1-10, "final_score": 1-10, "eu_angle": "hook for EU audience", "post_type": "news|tutorial|opinion|tool_launch"}}'''
    return call_mistral(prompt)


def save_to_content_queue(trend, score_data, velocity):
    if score_data['final_score'] < 7:
        print(f'  Score {score_data["final_score"]} — below threshold')
        return False

    title = trend.get('name', trend.get('tagline', ''))
    payload = {
        'title': title[:200],
        'source_url': '',
        'eu_angle': score_data.get('eu_angle', ''),
        'post_type': score_data.get('post_type', 'news'),
        'score': score_data['final_score'],
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
        print(f'  SAVED (score {score_data["final_score"]}, velocity {velocity:.0f}%): {title[:60]}')
        return True
    except Exception as e:
        print(f'  Error saving: {e}')
        return False


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Trend Amplifier started...')

    all_trends = []
    all_trends.extend(fetch_twitter_trends())
    all_trends.extend(fetch_youtube_trends())
    all_trends.extend(fetch_producthunt_trends())
    all_trends.extend(fetch_tiktok_trends())

    print(f'Total trends collected: {len(all_trends)}')

    hijacked = 0
    for trend in all_trends:
        time.sleep(2)
        name = trend.get('name', trend.get('tagline', ''))
        volume = trend.get('volume', 0)
        velocity = calculate_velocity(name, volume)
        save_trend_history(name, trend['source'], volume, velocity)
        result = score_trend(trend, velocity)
        if result:
            r = result.get('relevance', 0) * 0.5
            v = min(velocity / 100, 10) * 0.2 if velocity > 0 else 0
            vol = min(volume / 10000, 10) * 0.3
            base = r + v + vol
            if velocity > 50:
                base += 1
            result['final_score'] = round(min(base, 10), 1)
            if save_to_content_queue(trend, result, velocity):
                hijacked += 1

    print(f'Trend Amplifier done. Fast-published {hijacked} trends.')
    if hijacked > 0:
        print(f'  Breaking: production cycle triggered for these topics.')


if __name__ == '__main__':
    main()
