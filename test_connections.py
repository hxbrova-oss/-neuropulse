import requests
import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YOUR_CHAT_ID = os.getenv('YOUR_CHAT_ID')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

print('=== Testing Telegram Bot ===')
try:
    res = requests.get(
        f'https://api.telegram.org/bot{BOT_TOKEN}/getMe',
        timeout=10
    )
    print(f'Status: {res.status_code}')
    if res.status_code == 200:
        bot = res.json()['result']
        print(f'Bot name: {bot["first_name"]}')
        print(f'Bot username: @{bot["username"]}')
    else:
        print(f'Error: {res.text[:300]}')
except Exception as e:
    print(f'Error: {e}')

print()
print('=== Testing Groq API ===')
try:
    res = requests.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {GROQ_API_KEY}',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': 'Say hi'}],
            'max_tokens': 10
        },
        timeout=30
    )
    print(f'Status: {res.status_code}')
    if res.status_code == 200:
        msg = res.json()['choices'][0]['message']['content']
        print(f'OK - Response: {msg}')
    else:
        print(f'Error: {res.text[:500]}')
except Exception as e:
    print(f'Error: {e}')
