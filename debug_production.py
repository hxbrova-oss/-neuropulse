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

# Get pending topics
res = requests.get(
    f'{SUPABASE_URL}/rest/v1/content_queue?status=eq.pending&order=score.desc&limit=2',
    headers=HDR, timeout=15
)
topics = res.json()
print(f'Pending topics: {len(topics)}')

for topic in topics:
    print(f'\n--- {topic["title"][:50]} ---')
    
    angle = topic.get('eu_angle', topic.get('arabic_angle', 'General tech'))
    print(f'Angle: {angle}')
    
    prompt = f'''You are a senior tech content writer for a premium Telegram channel called "NeuroPulse" targeting English-speaking professionals in Central Europe (Germany, Switzerland, Austria, Netherlands).

AUDIENCE: Developers, SaaS founders, AI enthusiasts, finance professionals. Age 25-40.

TOPIC TO WRITE ABOUT:
Title: {topic["title"]}
Context/Angle: {angle}
Content Type: {topic.get("post_type", "news")}

YOUR TASK: Write a detailed, high-value Telegram post.

POST FORMAT:
[Hook line - 1 compelling sentence]

[Context - 2-3 sentences explaining what happened]

[Why it matters - 3-4 bullet points with real value]

[Actionable takeaway - 1-2 sentences]

[CTA - 1 line]

#AITools #Automation #TechEU #Productivity

RULES:
- Professional English, no fluff
- Be specific: real tools, real numbers
- NO emojis in body (max 2 in hook)
- 200-350 words
- Reply with JSON only:
{{
  "telegram_post": "The full post",
  "hashtags": ["AITools", "Automation", "TechEU", "Productivity"],
  "best_time": "morning|noon|evening"
}}'''

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
        print(f'API status: {res.status_code}')
        
        if res.status_code == 200:
            text = res.json()['choices'][0]['message']['content']
            cleaned = re.sub(r'```json\s*', '', text.strip())
            cleaned = re.sub(r'```\s*$', '', cleaned.strip())
            post_data = json.loads(cleaned)
            print(f'Post preview: {post_data.get("telegram_post", "")[:150]}...')
            
            # Update Supabase
            update_res = requests.patch(
                f'{SUPABASE_URL}/rest/v1/content_queue?id=eq.{topic["id"]}',
                headers={**HDR, 'Content-Type': 'application/json'},
                json={
                    'status': 'ready',
                    'telegram_post': post_data['telegram_post'],
                    'twitter_post': post_data.get('twitter_post', ''),
                    'hashtags': json.dumps(post_data['hashtags']),
                    'best_time': post_data['best_time'],
                },
                timeout=15
            )
            print(f'Update status: {update_res.status_code}')
            if update_res.status_code != 200:
                print(f'Update error: {update_res.text[:300]}')
        else:
            print(f'Error: {res.text[:300]}')
    except Exception as e:
        print(f'Error: {e}')
    
    time.sleep(5)
