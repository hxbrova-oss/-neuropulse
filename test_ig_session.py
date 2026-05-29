import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

SESSIONID = '80594145422%3A1WuEIMsaqHATa9%3A29%3AAYgGy9R_qy00IIyYkhE834m8XBkjww4eYGNpGyz3uQ'

print('Testing Instagram login with sessionid...')

try:
    from instagrapi import Client
    cl = Client()
    cl.login_by_sessionid(SESSIONID)
    
    user_id = cl.user_id
    username = cl.username
    print(f'Login successful!')
    print(f'User: {username} (ID: {user_id})')
    
    # Save session for reuse
    cl.dump_settings(os.path.join(os.environ.get('TEMP', '/tmp'), 'ig_session.json'))
    print('Session saved.')
    print('Instagram is ready!')
except Exception as e:
    print(f'Error: {e}')
