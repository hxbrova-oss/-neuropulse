import requests
import json
import os
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

CET = timezone(timedelta(hours=1))
HDR = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}


def get_hashtag_scores():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/hashtag_scores?order=score.desc',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f'Error fetching hashtag scores: {e}')
        return []


def get_published_hashtags():
    try:
        res = requests.get(
            f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.published&select=hashtags',
            headers=HDR, timeout=15
        )
        res.raise_for_status()
        rows = res.json()
        tags = []
        for r in rows:
            try:
                tags.extend(json.loads(r.get('hashtags', '[]')))
            except Exception:
                pass
        return tags
    except Exception as e:
        print(f'Error fetching hashtags: {e}')
        return []


def score_existing_hashtags(all_tags):
    scores = {}
    counts = {}
    for tag in all_tags:
        tag_lower = tag.lower()
        counts[tag_lower] = counts.get(tag_lower, 0) + 1
    for tag, count in counts.items():
        scores[tag] = min(count * 10, 100)
    return scores


def update_hashtag_scores(scores):
    now = datetime.now(CET).isoformat()
    for tag, score in scores.items():
        try:
            existing = requests.get(
                f'{SUPABASE_URL}/rest/v1/hashtag_scores?tag=eq.{tag}',
                headers=HDR, timeout=15
            ).json()
            if existing:
                old = existing[0]
                new_times = old['times_used'] + 1
                new_score = ((old['score'] * old['times_used']) + score) / new_times
                requests.patch(
                    f'{SUPABASE_URL}/rest/v1/hashtag_scores?tag=eq.{tag}',
                    headers={**HDR, 'Content-Type': 'application/json'},
                    json={'score': round(new_score, 1), 'times_used': new_times, 'last_updated': now},
                    timeout=15
                )
            else:
                requests.post(
                    f'{SUPABASE_URL}/rest/v1/hashtag_scores',
                    headers={**HDR, 'Content-Type': 'application/json'},
                    json={'tag': tag, 'score': score, 'times_used': 1, 'last_updated': now},
                    timeout=15
                )
        except Exception as e:
            print(f'  Error updating {tag}: {e}')


def generate_new_hashtags(count=10):
    prompt = f'''Generate {count} trending English hashtags for AI tools, SaaS, and tech productivity.

Target audience: English-speaking tech professionals in Central Europe (DE, CH, AT, NL), age 25-40.

Requirements:
- Mix of broad (#AITools, #Productivity) and niche tags
- Currently trending in tech Twitter/LinkedIn
- Single words only (no spaces)
- Return as JSON array of strings

Example: ["AITools", "Productivity", "Automation", "SaaS", "TechCareers", "FutureOfWork"]

Reply JSON only:
{{"hashtags": ["tag1", "tag2", ...]}}'''
    try:
        res = requests.post(
            'https://api.mistral.ai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {MISTRAL_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'mistral-large-latest',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.8,
                'max_tokens': 512
            },
            timeout=60
        )
        res.raise_for_status()
        data = json.loads(res.json()['choices'][0]['message']['content'])
        return data.get('hashtags', [])
    except Exception as e:
        print(f'Error generating hashtags: {e}')
        return ['AITools', 'Automation', 'TechEU', 'Productivity', 'SaaS']


def main():
    now_cet = datetime.now(CET)
    print(f'[{now_cet.strftime("%H:%M")} CET] Hashtag Optimizer started...')

    all_tags = get_published_hashtags()
    print(f'Found {len(all_tags)} hashtag uses in published posts')

    scores = score_existing_hashtags(all_tags)
    update_hashtag_scores(scores)

    current = get_hashtag_scores()
    print(f'Scored {len(current)} unique hashtags')

    if len(current) >= 10:
        sorted_tags = sorted(current, key=lambda x: x['score'])
        drop_count = max(1, int(len(sorted_tags) * 0.2))
        bottom = sorted_tags[:drop_count]
        print(f'Bottom {drop_count} tags to replace:')
        for t in bottom:
            print(f'  #{t["tag"]} (score {t["score"]})')
            try:
                requests.delete(
                    f'{SUPABASE_URL}/rest/v1/hashtag_scores?tag=eq.{t["tag"]}',
                    headers=HDR, timeout=15
                )
            except Exception:
                pass

    print('Generating fresh hashtags...')
    time.sleep(2)
    new_tags = generate_new_hashtags(10)
    print(f'Generated {len(new_tags)} new hashtag suggestions')
    for tag in new_tags:
        print(f'  #{tag}')

    if new_tags:
        print('\nRecommended tags for next posts:')
        print(', '.join(f'#{t}' for t in new_tags[:5]))

    print('Hashtag Optimizer done.')


if __name__ == '__main__':
    main()
