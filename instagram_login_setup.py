from instagrapi import Client
from dotenv import load_dotenv
import os, sys

load_dotenv(dotenv_path=r'C:\Users\abdal\Desktop\100 free\autonomous_profit_system\.env')

cl = Client()
cl.delay_range = [1, 3]

def challenge_handler(challenge_url):
    print(f'\nChallenge URL: {challenge_url}')
    code = input('Enter the verification code sent to your email/phone: ')
    return code

cl.challenge_code_handler = challenge_handler

username = os.getenv('IG_USERNAME')
password = os.getenv('IG_PASSWORD')

try:
    cl.login(username, password)
    print(f'Login OK! User: {cl.user_id}')
    session_path = os.path.join(os.path.dirname(__file__), 'instagram_session.json')
    cl.dump_settings(session_path)
    print(f'Saved to {session_path}')
except Exception as e:
    print(f'Failed: {e}')
    sys.exit(1)
