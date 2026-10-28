import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Validate required environment variables
REQUIRED_ENV_VARS = [
    'WHATSAPP_API_TOKEN',
    'WHATSAPP_PHONE_NUMBER_ID',
    'SPITCH_API_KEY',
    'WEBHOOK_VERIFY_TOKEN'
]

missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]

if missing_vars:
    print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set these variables in your Railway deployment settings.")
else:
    print("All required environment variables are present")

# Environment variables
WHATSAPP_API_TOKEN = os.getenv('WHATSAPP_API_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
SPITCH_API_KEY = os.getenv('SPITCH_API_KEY')
WEBHOOK_VERIFY_TOKEN = os.getenv('WEBHOOK_VERIFY_TOKEN')

# Storage paths
PREFERENCES_FILE = '/tmp/user_preferences.json' if os.path.exists('/tmp') else 'user_preferences.json'
WELCOMED_FILE = '/tmp/welcomed_users.json' if os.path.exists('/tmp') else 'welcomed_users.json'

# Language and voice configurations
LANGUAGE_NAMES = {
    'yo': 'Yoruba',
    'ig': 'Igbo',
    'ha': 'Hausa',
    'en': 'English'
}

VOICE_MAPPING = {
    'yo': 'sade',      # Yoruba voice
    'ig': 'ngozi',     # Igbo voice
    'ha': 'amina',     # Hausa voice
    'en': 'lucy',      # English voice
    'am': 'selam'      # Amharic voice
}

LANGUAGE_PREFIXES = {
    '/yoruba': 'yo',
    '/igbo': 'ig',
    '/hausa': 'ha',
    '/english': 'en'
}
