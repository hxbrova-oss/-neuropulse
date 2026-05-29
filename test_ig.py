import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

IG_USERNAME = os.getenv('IG_USERNAME', '')
IG_PASSWORD = os.getenv('IG_PASSWORD', '')

print(f'Testing Instagram login for: {IG_USERNAME}')

try:
    from instagrapi import Client
    cl = Client()
    cl.login(IG_USERNAME, IG_PASSWORD)
    
    user_id = cl.user_id_from_username(IG_USERNAME)
    print(f'Login successful!')
    print(f'User ID: {user_id}')
    
    # Save session
    cl.dump_settings(os.path.join(os.environ.get('TEMP', '/tmp'), 'ig_session.json'))
    print('Session saved.')
except Exception as e:
    print(f'Error: {e}')
