import requests

MISTRAL_KEY = 'eWX6V9uezDIHXGoHfFNEdFOB3geKxnJr'

print('Testing Mistral API...')
try:
    res = requests.post(
        'https://api.mistral.ai/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {MISTRAL_KEY}',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'mistral-large-latest',
            'messages': [{'role': 'user', 'content': 'Say hi in Arabic one word only'}],
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
