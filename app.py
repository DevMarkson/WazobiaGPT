from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import json
from spitch import Spitch
import time
from pydub import AudioSegment
from pydub.utils import which
import tempfile
import subprocess
import sys
import traceback

# Load environment variables
load_dotenv()

# Validate required environment variables
required_env_vars = [
    'WHATSAPP_API_TOKEN',
    'WHATSAPP_PHONE_NUMBER_ID',
    'SPITCH_API_KEY',
    'WEBHOOK_VERIFY_TOKEN'
]

missing_vars = []
for var in required_env_vars:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    print(
        f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set these variables in your Railway deployment settings.")
else:
    print("All required environment variables are present")

# Configure ffmpeg for pydub
try:
    import imageio_ffmpeg as ffmpeg
    ffmpeg_path = ffmpeg.get_ffmpeg_exe()
    AudioSegment.converter = ffmpeg_path
    AudioSegment.ffmpeg = ffmpeg_path
    AudioSegment.ffprobe = ffmpeg_path.replace("ffmpeg", "ffprobe")
    print(f"Configured ffmpeg from imageio-ffmpeg: {ffmpeg_path}")
except Exception as e:
    print(f"Could not configure imageio-ffmpeg: {e}")

app = Flask(__name__)

# Simple in-memory cache to track processed messages with timestamps
processed_messages = {}

# Persistent storage for user language preferences
PREFERENCES_FILE = '/tmp/user_preferences.json' if os.path.exists(
    '/tmp') else 'user_preferences.json'


def load_user_preferences():
    """Load user preferences from file"""
    try:
        if os.path.exists(PREFERENCES_FILE):
            with open(PREFERENCES_FILE, 'r') as f:
                preferences = json.load(f)
                print(f"Loaded {len(preferences)} user preferences from file")
                return preferences
    except Exception as e:
        print(f"Error loading preferences: {e}")
    return {}


def save_user_preferences(preferences):
    """Save user preferences to file"""
    try:
        with open(PREFERENCES_FILE, 'w') as f:
            json.dump(preferences, f)
            print(f"Saved {len(preferences)} user preferences to file")
    except Exception as e:
        print(f"Error saving preferences: {e}")


def load_welcomed_users():
    """Load list of users who have been welcomed"""
    try:
        welcomed_file = '/tmp/welcomed_users.json' if os.path.exists(
            '/tmp') else 'welcomed_users.json'
        if os.path.exists(welcomed_file):
            with open(welcomed_file, 'r') as f:
                welcomed = json.load(f)
                print(f"Loaded {len(welcomed)} welcomed users from file")
                return set(welcomed)
    except Exception as e:
        print(f"Error loading welcomed users: {e}")
    return set()


def save_welcomed_users(welcomed_users):
    """Save list of welcomed users to file"""
    try:
        welcomed_file = '/tmp/welcomed_users.json' if os.path.exists(
            '/tmp') else 'welcomed_users.json'
        with open(welcomed_file, 'w') as f:
            json.dump(list(welcomed_users), f)
            print(f"Saved {len(welcomed_users)} welcomed users to file")
    except Exception as e:
        print(f"Error saving welcomed users: {e}")


# Load existing preferences and welcomed users on startup
user_language_preferences = load_user_preferences()
welcomed_users = load_welcomed_users()


def enhance_igbo_text_with_diacritics(text):
    """Add proper Igbo diacritics to common words"""
    igbo_word_map = {
        'chineke': 'Chineke',  # God
        'ndewo': 'Ndeewo',     # Hello
        'kedu': 'Kedụ',        # How
        'ime': 'ịme',          # to do
        'umu': 'ụmụ',          # children
        'nwa': 'nwa',          # child
        'anya': 'anya',        # eye
        'obi': 'obi',          # heart
        'ulo': 'ụlọ',          # house
        'aha': 'aha',          # name
        'onye': 'onye',        # person
        'ugbo': 'ụgbọ',        # vehicle
        'uche': 'uche',        # wisdom/mind
        'chi': 'chi',          # personal god/destiny
        'eze': 'eze',          # king
        'ada': 'ada',          # first daughter
        'nna': 'nna',          # father
        'nne': 'nne',          # mother
        'nwanne': 'nwanne',    # sibling
        'egwu': 'egwu',        # music/dance
        'oji': 'ọjị',          # kola nut
        'mmiri': 'mmiri',      # water
        'anwu': 'anwụ',        # sun
        'onwa': 'ọnwa',        # moon
        'kpakpando': 'kpakpando',  # star
    }

    # Convert to lowercase for matching, but preserve original case
    words = text.split()
    enhanced_words = []

    for word in words:
        # Remove punctuation for matching
        clean_word = word.lower().strip('.,!?;:')
        if clean_word in igbo_word_map:
            # Replace with enhanced version, preserving punctuation
            enhanced = igbo_word_map[clean_word]
            # Preserve original case pattern
            if word.isupper():
                enhanced = enhanced.upper()
            elif word.istitle():
                enhanced = enhanced.capitalize()

            # Add back punctuation
            punctuation = ''
            for char in word[::-1]:
                if char in '.,!?;:':
                    punctuation = char + punctuation
                else:
                    break
            enhanced_words.append(enhanced + punctuation)
        else:
            enhanced_words.append(word)

    return ' '.join(enhanced_words)


def enhance_yoruba_text_with_diacritics(text):
    """Add proper Yoruba diacritics to common words"""
    yoruba_word_map = {
        'bawo': 'Báwo',        # How
        'ni': 'ni',            # is/are
        'se': 'ṣe',            # to do/make
        'omo': 'ọmọ',          # child
        'oko': 'ọkọ',          # husband/vehicle
        'ile': 'ilé',          # house
        'eko': 'Èkó',          # Lagos
        'oba': 'ọba',          # king
        'oye': 'òye',          # title/position
        'ire': 'ire',          # good/blessing
        'aje': 'àjẹ',          # wealth/witch
        'owo': 'owó',          # money
        'ori': 'orí',          # head/destiny
        'emi': 'èmi',          # I/me
        'iwo': 'ìwọ',          # you
        'awa': 'àwa',          # we
        'eyin': 'ẹ̀yin',        # you (plural)
        'won': 'wọn',          # they
        'ti': 'tí',            # of/from
        'si': 'sí',            # to/at
        'fun': 'fún',          # for
        'ni': 'ní',            # at/in
        'pe': 'pé',            # that/to call
        'ki': 'kí',            # to/let
        'ma': 'má',            # don't
        'ko': 'kò',            # not
        'da': 'dá',            # to create/pour
        'wa': 'wá',            # to come/to be
        'lo': 'lọ',            # to go
        'gbo': 'gbọ́',          # to hear
        'ri': 'rí',            # to see
        'je': 'jẹ',            # to eat/to be
        'mu': 'mú',            # to drink/to take
        'sun': 'sùn',          # to sleep
        'dide': 'dìde',        # to stand up
        'joko': 'jókòó',       # to sit
    }

    # Convert to lowercase for matching, but preserve original case
    words = text.split()
    enhanced_words = []

    for word in words:
        # Remove punctuation for matching
        clean_word = word.lower().strip('.,!?;:')
        if clean_word in yoruba_word_map:
            # Replace with enhanced version, preserving punctuation
            enhanced = yoruba_word_map[clean_word]
            # Preserve original case pattern
            if word.isupper():
                enhanced = enhanced.upper()
            elif word.istitle():
                enhanced = enhanced.capitalize()

            # Add back punctuation
            punctuation = ''
            for char in word[::-1]:
                if char in '.,!?;:':
                    punctuation = char + punctuation
                else:
                    break
            enhanced_words.append(enhanced + punctuation)
        else:
            enhanced_words.append(word)

    return ' '.join(enhanced_words)


def get_welcome_message():
    """Generate welcome message for new users"""
    return """🤖 Welcome to Spitch Translator Bot! 

I can help you with:

🎯 SET LANGUAGE PREFERENCE:
• /yoruba - Set Yoruba as default
• /igbo - Set Igbo as default
• /hausa - Set Hausa as default
• /english - Set English as default

🎤 AUDIO FEATURES:
• Send voice notes - Auto transcribe & translate
• /speak [text] - Text to speech in your set language
  Example: /speak Báwo ni (How are you in Yoruba)

💬 TEXT TRANSLATION:
• Set a language preference first, then send any text
• I'll automatically translate it for you!

📋 OTHER COMMANDS:
• /help - Show this help message
• /commands - Show all available commands
• /reset - Clear your language preference

Just send me text or voice messages and I'll help translate them! 🌍"""


def get_help_message():
    """Generate detailed help message"""
    return """🎤WAZOBIA TRANSLATOR BOT HELP

🌍 SUPPORTED LANGUAGES:
• Yoruba (yo) - /yoruba
• Igbo (ig) - /igbo  
• Hausa (ha) - /hausa
• English (en) - /english

🎯 SET LANGUAGE PREFERENCE:
   /yoruba → Sets Yoruba as your default
   /igbo → Sets Igbo as your default
   
💬 TEXT TRANSLATION:
   1. Set language preference: /yoruba
   2. Send text: "Báwo ni"
   3. Get: "Text (Yoruba): Báwo ni
      English translation: How are you"

🎤 VOICE FEATURES:
• Send voice notes → Auto transcribe + translate
• Voice notes use your set language preference
• Supports Yoruba, Igbo, Hausa and English
• Other Nigerian languages coming soon!


🔊 TEXT-TO-SPEECH:
• /speak [text] → Voice in your set language
  Examples:
  - Set /yoruba, then /speak Báwo ni
  - Set /igbo, then /speak Ndeewo
  - Set /hausa, then /speak Sannu

⚙️ SETTINGS COMMANDS:
• /help - This help message
• /commands - Quick command list  
• /reset - Clear language preference
• /status - Check your current settings

Just send me text or voice messages and I'll help translate them! 🤗"""


def get_commands_list():
    """Generate quick commands reference"""
    return """⚡ QUICK COMMANDS REFERENCE

🎯 LANGUAGE PREFERENCES:
/yoruba - Set Yoruba default
/igbo - Set Igbo default  
/hausa - Set Hausa default
/english - Set English default

� TEXT-TO-SPEECH:
/speak [text] - Generate speech in your set language
  Example: /speak Báwo ni (after setting /yoruba)

🎤 AUDIO FEATURES:
• Send voice notes - Auto transcribe & translate
• Uses your language preference

ℹ️ INFO COMMANDS:
/help - Detailed help
/commands - This list
/status - Your settings
/reset - Clear preferences

💬 Set language preference, then send text or voice! 🌍"""


def get_status_message(sender):
    """Generate user status message"""
    user_preference = user_language_preferences.get(sender)
    language_names = {
        'yo': 'Yoruba',
        'ig': 'Igbo',
        'ha': 'Hausa',
        'en': 'English'
    }

    if user_preference:
        lang_name = language_names.get(user_preference, 'Unknown')
        return f"""📊 YOUR CURRENT SETTINGS

🎯 Default Language: {lang_name} ({user_preference})
✅ Status: Active

Your text and voice messages will be processed in {lang_name} unless you specify otherwise.

To change: Send /{lang_name.lower()} to set a new preference
To clear: Send /reset"""
    else:
        return """📊 YOUR CURRENT SETTINGS

🎯 Default Language: Not set
⚪ Status: Auto-detect mode

I'll try to detect your language automatically. For better accuracy, set a default language:

/yoruba - Set Yoruba as default
/igbo - Set Igbo as default
/hausa - Set Hausa as default  
/english - Set English as default"""


def send_welcome_to_new_user(sender):
    """Send welcome message to new users"""
    # Check if user has been welcomed before
    if sender not in welcomed_users:
        welcomed_users.add(sender)
        save_welcomed_users(welcomed_users)
        return True
    return False


def cleanup_old_messages():
    """Remove messages older than 1 hour from the cache"""
    current_time = time.time()
    one_hour_ago = current_time - 3600  # 3600 seconds = 1 hour

    messages_to_remove = []
    for message_id, timestamp in processed_messages.items():
        if timestamp < one_hour_ago:
            messages_to_remove.append(message_id)

    for message_id in messages_to_remove:
        del processed_messages[message_id]

    print(f"Cleaned up {len(messages_to_remove)} old messages from cache")


def extract_language_prefix(text):
    """Extract language prefix from text and return (language_code, cleaned_text, is_preference_setting, is_tts_request)"""
    language_prefixes = {
        '/yoruba': 'yo',
        '/igbo': 'ig',
        '/hausa': 'ha',
        '/english': 'en'
    }

    # Check for TTS commands first
    tts_commands = ['/speak']
    text_lower = text.lower().strip()

    for tts_cmd in tts_commands:
        if text_lower.startswith(tts_cmd):
            # Remove the TTS command
            remaining_text = text[len(tts_cmd):].strip()

            # Check if a language is specified after TTS command
            for prefix, lang_code in language_prefixes.items():
                lang_name = prefix[1:]  # Remove the '/' from prefix
                if remaining_text.lower().startswith(lang_name):
                    # Remove the language name and get the text to convert
                    text_to_convert = remaining_text[len(lang_name):].strip()
                    return lang_code, text_to_convert, False, True

            # No specific language mentioned, use default behavior
            return None, remaining_text, False, True

    # Check for regular language prefixes (for transcription/translation)
    for prefix, lang_code in language_prefixes.items():
        if text_lower.startswith(prefix):
            # Remove the prefix and any whitespace after it
            cleaned_text = text[len(prefix):].strip()

            # If there's no text after the prefix, it's a preference setting
            is_preference_setting = len(cleaned_text) == 0

            return lang_code, cleaned_text, is_preference_setting, False

    return None, text, False, False


def configure_ffmpeg():
    """Configure ffmpeg path for pydub"""
    try:
        import imageio_ffmpeg as ffmpeg
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffmpeg = ffmpeg_path
        AudioSegment.ffprobe = ffmpeg_path.replace("ffmpeg", "ffprobe")
        print(f"Using ffmpeg from imageio-ffmpeg: {ffmpeg_path}")
        return True
    except ImportError:
        print("imageio-ffmpeg not available")
        return False
    except Exception as e:
        print(f"Error configuring ffmpeg: {e}")
        return False


def convert_wav_to_compatible_format(wav_filename):
    """Try multiple methods to convert WAV to WhatsApp-compatible format"""

    # First, try to configure ffmpeg
    ffmpeg_configured = configure_ffmpeg()

    # Method 1: Try pydub with configured ffmpeg
    if ffmpeg_configured:
        try:
            print("Attempting conversion with pydub and imageio-ffmpeg...")
            audio = AudioSegment.from_wav(wav_filename)
            mp3_filename = wav_filename.replace('.wav', '.mp3')
            audio.export(mp3_filename, format="mp3", bitrate="128k")

            if os.path.exists(mp3_filename):
                print(f"Successfully converted to MP3: {mp3_filename}")
                return mp3_filename, "audio/mpeg"
        except Exception as e:
            print(f"Pydub with imageio-ffmpeg conversion failed: {e}")

    # Method 2: Try pydub without specific ffmpeg configuration (fallback)
    try:
        print("Attempting conversion with default pydub...")
        audio = AudioSegment.from_wav(wav_filename)
        mp3_filename = wav_filename.replace('.wav', '.mp3')
        audio.export(mp3_filename, format="mp3", bitrate="128k")

        if os.path.exists(mp3_filename):
            return mp3_filename, "audio/mpeg"
    except Exception as e:
        print(f"Default pydub conversion failed: {e}")

    # Method 3: Try converting to OGG using pydub (simpler conversion)
    try:
        print("Attempting conversion to OGG...")
        audio = AudioSegment.from_wav(wav_filename)
        ogg_filename = wav_filename.replace('.wav', '.ogg')
        audio.export(ogg_filename, format="ogg")

        if os.path.exists(ogg_filename):
            return ogg_filename, "audio/ogg"
    except Exception as e:
        print(f"OGG conversion failed: {e}")

    # If all conversions fail, return None to indicate failure
    print("All conversion methods failed")
    return None, None


def generate_speech_audio(text, language_code, client):
    """Generate speech audio using Spitch API and convert to MP3 if possible"""
    # Voice mapping for each language
    voice_mapping = {
        'yo': 'sade',      # Yoruba voice
        'ig': 'ngozi',     # Igbo voice (updated to available voice)
        'ha': 'amina',     # Hausa voice
        'en': 'lucy',      # English voice (updated to available voice)
        'am': 'selam'      # Amharic voice (updated to available voice)
    }

    # Default to English voice
    voice = voice_mapping.get(language_code, 'lucy')

    try:
        print(
            f"Generating speech for text: '{text}' in language: {language_code} with voice: {voice}")

        # Generate speech with Spitch (returns WAV format)
        response = client.speech.generate(
            text=text,
            language=language_code,
            voice=voice
        )

        # Create temporary WAV file
        temp_wav_filename = f"temp_tts_{int(time.time())}.wav"
        with open(temp_wav_filename, "wb") as f:
            f.write(response.read())

        # Try to convert to WhatsApp-compatible format
        converted_filename, content_type = convert_wav_to_compatible_format(
            temp_wav_filename)

        if converted_filename and os.path.exists(converted_filename):
            # Conversion successful
            try:
                os.remove(temp_wav_filename)
            except Exception as cleanup_error:
                print(
                    f"Warning: Could not remove temp file {temp_wav_filename}: {cleanup_error}")

            print(
                f"Speech generated and converted successfully: {converted_filename}")
            return converted_filename, content_type
        else:
            # All conversions failed - we cannot use WAV as WhatsApp doesn't support it
            # Clean up and return None to indicate failure
            try:
                os.remove(temp_wav_filename)
            except Exception as cleanup_error:
                print(
                    f"Warning: Could not remove temp file {temp_wav_filename}: {cleanup_error}")

            print("Failed to convert audio to WhatsApp-compatible format")
            return None, None

    except Exception as e:
        print(f"Error generating speech: {str(e)}")
        return None


def is_low_quality_transcription(transcription):
    """Check if transcription appears to be low quality/noise"""
    if not transcription or len(transcription.strip()) == 0:
        return True

    words = transcription.split()

    # Too few words (likely noise)
    if len(words) < 2:
        return True

    # Check for excessive repetition
    unique_words = set(words)
    repetition_ratio = len(
        words) / len(unique_words) if len(unique_words) > 0 else 0

    # If more than 70% of the words are repetitive, it's likely noise
    if repetition_ratio > 5:
        print(f"High repetition detected: {repetition_ratio:.1f}x average")
        return True

    # Check for very long transcriptions with repetitive patterns (like the Igbo example)
    if len(words) > 50:
        # Look for patterns like "mmepe, mmepe, mmepe" or "na-enwe mmetụta"
        word_frequency = {}
        for word in words:
            word_frequency[word] = word_frequency.get(word, 0) + 1

        # If any single word appears more than 30% of the time in a long text, it's likely noise
        max_frequency = max(word_frequency.values()) if word_frequency else 0
        if max_frequency > len(words) * 0.3:
            print(
                f"Single word dominance detected: {max_frequency}/{len(words)} words")
            return True

    # Check for very short repetitive words that are likely artifacts
    short_repetitive_words = [word for word in words if len(word) <= 3]
    if len(short_repetitive_words) > len(words) * 0.7:  # More than 70% very short words
        print(
            f"Too many short words: {len(short_repetitive_words)}/{len(words)}")
        return True

    return False


@app.route('/debug-preferences', methods=['GET'])
def debug_preferences():
    """Debug endpoint to check user language preferences"""
    return jsonify({
        "status": "success",
        "user_preferences": user_language_preferences,
        "total_users": len(user_language_preferences)
    }), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    env_status = {}
    required_vars = ['WHATSAPP_API_TOKEN', 'WHATSAPP_PHONE_NUMBER_ID',
                     'SPITCH_API_KEY', 'WEBHOOK_VERIFY_TOKEN']

    for var in required_vars:
        env_status[var] = "Present" if os.getenv(var) else "Missing"

    return jsonify({
        "status": "healthy",
        "environment_variables": env_status,
        "timestamp": time.time()
    }), 200


@app.route('/test-spitch', methods=['GET'])
def test_spitch():
    """Test endpoint to verify Spitch API is working"""
    try:
        spitch_api_key = os.getenv("SPITCH_API_KEY")
        if not spitch_api_key:
            return jsonify({"status": "error", "message": "SPITCH_API_KEY not set"}), 500

        # Set the API key in environment (required by Spitch SDK)
        os.environ["SPITCH_API_KEY"] = spitch_api_key
        client = Spitch()

        # Try a simple translation test
        test_text = "Hello world"
        response = client.text.translate(
            text=test_text,
            source="en",
            target="yo"
        )

        return jsonify({
            "status": "success",
            "message": "Spitch API is working",
            "test_translation": response.text,
            "original": test_text
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Spitch API test failed: {str(e)}",
            "error_type": type(e).__name__
        }), 500


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verify token
        verify_token = os.getenv('WEBHOOK_VERIFY_TOKEN')
        if request.args.get('hub.verify_token') == verify_token:
            return request.args.get('hub.challenge'), 200
        return 'Forbidden', 403

    elif request.method == 'POST':
        try:
            data = request.json
            print("Received webhook data:", json.dumps(data, indent=2))

            # Check if this is a WhatsApp message with audio
            if ('entry' in data and len(data['entry']) > 0 and
                'changes' in data['entry'][0] and len(data['entry'][0]['changes']) > 0 and
                'value' in data['entry'][0]['changes'][0] and
                    'messages' in data['entry'][0]['changes'][0]['value']):

                messages = data['entry'][0]['changes'][0]['value']['messages']
                for message in messages:
                    if message.get('type') == 'audio':
                        try:
                            # Clean up old messages periodically
                            if len(processed_messages) > 100:
                                cleanup_old_messages()

                            # Get media ID and sender
                            media_id = message['audio']['id']
                            sender = message['from']
                            message_id = message['id']

                            # Check if we've already processed this message
                            if message_id in processed_messages:
                                print(
                                    f"Message {message_id} already processed, skipping...")
                                return jsonify({"status": "already processed"}), 200

                            # Add message to processed set with current timestamp
                            processed_messages[message_id] = time.time()
                            print(
                                f"Processing audio message {media_id} from {sender} (message_id: {message_id})")

                            # Get media URL
                            media_url = f"https://graph.facebook.com/v22.0/{media_id}"
                            headers = {
                                'Authorization': f'Bearer {os.getenv("WHATSAPP_API_TOKEN")}'
                            }

                            # First, get the media URL
                            print(
                                f"Attempting to get media info from: {media_url}")
                            print(
                                f"Using headers: Authorization Bearer {os.getenv('WHATSAPP_API_TOKEN')[:20]}...")

                            media_info_response = requests.get(
                                media_url, headers=headers)

                            print(
                                f"Media info response status: {media_info_response.status_code}")
                            print(
                                f"Media info response headers: {dict(media_info_response.headers)}")

                            if media_info_response.status_code != 200:
                                print(
                                    f"Failed to get media URL. Status: {media_info_response.status_code}")
                                print(f"Response: {media_info_response.text}")

                                # Try to parse the error response
                                try:
                                    error_data = media_info_response.json()
                                    error_message = error_data.get(
                                        'error', {}).get('message', 'Unknown error')
                                    print(
                                        f"WhatsApp API Error: {error_message}")
                                    return jsonify({"status": "error", "message": f"WhatsApp API Error: {error_message}"}), 500
                                except:
                                    return jsonify({"status": "error", "message": f"Failed to get media URL (Status: {media_info_response.status_code})"}), 500

                            media_info = media_info_response.json()
                            print(f"Media info response: {media_info}")

                            if 'url' not in media_info:
                                print(f"No URL in media info: {media_info}")
                                return jsonify({"status": "error", "message": "No media URL found"}), 500

                            # Download the audio file
                            download_response = requests.get(
                                media_info['url'],
                                headers=headers
                            )
                            if download_response.status_code != 200:
                                print(
                                    f"Failed to download audio. Status: {download_response.status_code}")
                                return jsonify({"status": "error", "message": "Failed to download audio"}), 500

                            # Save the audio file to temporary directory
                            import tempfile
                            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                                temp_file.write(download_response.content)
                                audio_file = temp_file.name
                            print(
                                f"Audio file saved successfully: {audio_file}")

                            # Transcribe with Spitch SDK
                            try:
                                # Set up Spitch client
                                spitch_api_key = os.getenv("SPITCH_API_KEY")
                                print(
                                    f"Spitch API Key present: {'Yes' if spitch_api_key else 'No'}")
                                if not spitch_api_key:
                                    print(
                                        "SPITCH_API_KEY is not set in environment variables")
                                    return jsonify({"status": "error", "message": "Spitch API key not configured"}), 500

                                # Set the API key in environment (required by Spitch SDK)
                                os.environ["SPITCH_API_KEY"] = spitch_api_key
                                client = Spitch()
                                print("Spitch client initialized successfully")

                                # Read the audio file
                                with open(audio_file, "rb") as f:
                                    audio_content = f.read()
                                    print(
                                        f"Transcribing audio file: {audio_file}")

                                # List of languages to try (African languages first, then English)
                                # Yoruba, Igbo, Hausa, English
                                languages_to_try = ['yo', 'ig', 'ha', 'en']
                                language_names = {
                                    'yo': 'Yoruba',
                                    'ig': 'Igbo',
                                    'ha': 'Hausa',
                                    'en': 'English'
                                }

                                best_transcription = ""
                                detected_language = ""
                                best_confidence = 0

                                # Check if user has a language preference set
                                user_preferred_language = user_language_preferences.get(
                                    sender)

                                if user_preferred_language:
                                    # User has specified a language preference, use it directly
                                    print(
                                        f"Using user's preferred language: {language_names[user_preferred_language]} ({user_preferred_language})")
                                    try:
                                        response = client.speech.transcribe(
                                            language=user_preferred_language, content=audio_content)
                                        transcription = response.text.strip()

                                        if transcription and len(transcription) > 0:
                                            if not is_low_quality_transcription(transcription):
                                                best_transcription = transcription
                                                detected_language = user_preferred_language
                                                best_confidence = len(
                                                    transcription.split())
                                                print(
                                                    f"Transcription with preferred language: '{transcription}'")
                                            else:
                                                print(
                                                    "Low quality transcription detected with preferred language")

                                    except Exception as lang_error:
                                        print(
                                            f"Error transcribing with preferred language {language_names[user_preferred_language]}: {str(lang_error)}")

                                # If no user preference or transcription failed, try all languages
                                if not best_transcription:
                                    # Try each language and find the best result
                                    for lang_code in languages_to_try:
                                        try:
                                            print(
                                                f"Trying transcription with language: {language_names[lang_code]} ({lang_code})")
                                            response = client.speech.transcribe(
                                                language=lang_code, content=audio_content)
                                            transcription = response.text.strip()

                                            if transcription and len(transcription) > 0:
                                                # Check if this transcription is low quality/noise
                                                if is_low_quality_transcription(transcription):
                                                    print(
                                                        f"  {language_names[lang_code]}: Low quality transcription detected, skipping")
                                                    continue

                                                # Simple heuristic: longer transcription with actual words might be better
                                                # You could also use confidence scores if available in the response
                                                # Word count as confidence metric
                                                confidence = len(
                                                    transcription.split())
                                                print(
                                                    f"  {language_names[lang_code]}: '{transcription}' (confidence: {confidence})")

                                                if confidence > best_confidence:
                                                    best_transcription = transcription
                                                    detected_language = lang_code
                                                    best_confidence = confidence

                                        except Exception as lang_error:
                                            print(
                                                f"  Error with {language_names[lang_code]}: {str(lang_error)}")
                                            continue

                                if not best_transcription:
                                    print(
                                        "No successful transcription from any language")
                                    return jsonify({"status": "error", "message": "No transcription result"}), 500

                                # Final quality check on the best transcription
                                if is_low_quality_transcription(best_transcription):
                                    print(
                                        f"Best transcription failed quality check: '{best_transcription[:100]}...'")
                                    return jsonify({"status": "error", "message": "Audio quality too poor for transcription"}), 400

                                print(
                                    f"Best transcription in {language_names[detected_language]}: '{best_transcription}'")

                                # Prepare response message
                                if detected_language == 'en':
                                    # If English was detected, just return the transcription
                                    response_message = f"Transcription ({language_names[detected_language]}): {best_transcription}"
                                else:
                                    # If African language was detected, show both original and English translation
                                    response_message = f"Transcription ({language_names[detected_language]}): {best_transcription}"

                                    # Translate the transcribed text to English
                                    try:
                                        print(
                                            f"Translating '{best_transcription}' from {detected_language} to English...")
                                        translation_response = client.text.translate(
                                            text=best_transcription,
                                            source=detected_language,
                                            target="en"
                                        )
                                        english_translation = translation_response.text.strip()
                                        if english_translation:
                                            response_message += f"\n\nEnglish translation: {english_translation}"
                                            print(
                                                f"Translation result: {english_translation}")
                                        else:
                                            print(
                                                "Translation returned empty result")
                                    except Exception as translation_error:
                                        print(
                                            f"Could not translate text: {str(translation_error)}")
                                        response_message += f"\n\n(Translation unavailable: {str(translation_error)})"

                                transcription = response_message

                                # Clean up the temporary audio file
                                try:
                                    os.remove(audio_file)
                                    print(
                                        f"Cleaned up audio file: {audio_file}")
                                except Exception as cleanup_error:
                                    print(
                                        f"Warning: Could not clean up audio file {audio_file}: {str(cleanup_error)}")

                            except Exception as e:
                                print(
                                    f"Error with Spitch transcription: {str(e)}")
                                return jsonify({
                                    "status": "error",
                                    "message": f"Transcription error: {str(e)}"
                                }), 500

                            # For now, let's skip translation and just send the transcription
                            # You can add translation later if needed
                            translation = ""  # Placeholder for translation

                            # Send response via WhatsApp
                            whatsapp_url = f"https://graph.facebook.com/v22.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
                            response_data = {
                                "messaging_product": "whatsapp",
                                "to": sender,
                                "text": {
                                    "body": transcription
                                }
                            }
                            send_response = requests.post(
                                whatsapp_url,
                                headers={
                                    'Authorization': f'Bearer {os.getenv("WHATSAPP_API_TOKEN")}',
                                    'Content-Type': 'application/json'
                                },
                                json=response_data
                            )

                            if send_response.status_code != 200:
                                print(
                                    f"Failed to send WhatsApp response. Status: {send_response.status_code}")
                                print(f"Response: {send_response.text}")
                                return jsonify({"status": "error", "message": "Failed to send WhatsApp response"}), 500

                            print("Successfully processed audio and sent response")
                            return jsonify({"status": "success"}), 200

                        except Exception as e:
                            print(f"Error processing audio message: {str(e)}")
                            return jsonify({"status": "error", "message": str(e)}), 500

                    elif message.get('type') == 'text':
                        try:
                            # Clean up old messages periodically
                            if len(processed_messages) > 100:
                                cleanup_old_messages()

                            # Get text content and sender
                            text_content = message['text']['body']
                            sender = message['from']
                            message_id = message['id']

                            # Check if we've already processed this message
                            if message_id in processed_messages:
                                print(
                                    f"Text message {message_id} already processed, skipping...")
                                return jsonify({"status": "already processed"}), 200

                            # Add message to processed set with current timestamp
                            processed_messages[message_id] = time.time()
                            print(
                                f"Processing text message from {sender} (message_id: {message_id}): '{text_content}'")

                            # Check for help and info commands first
                            text_lower = text_content.lower().strip()

                            # Handle help commands
                            if text_lower in ['/help', 'help', '/h']:
                                response_message = get_help_message()
                            elif text_lower in ['/commands', '/cmd', 'commands']:
                                response_message = get_commands_list()
                            elif text_lower in ['/status', 'status']:
                                response_message = get_status_message(sender)
                            elif text_lower in ['/reset', 'reset']:
                                if sender in user_language_preferences:
                                    del user_language_preferences[sender]
                                    save_user_preferences(
                                        user_language_preferences)
                                    response_message = "✅ Language preference cleared! I'll now auto-detect languages for your messages.\n\nTo set a new preference, use:\n/yoruba /igbo /hausa /english"
                                else:
                                    response_message = "ℹ️ You don't have any language preference set. Use /help to see available commands."
                            elif text_lower in ['/start', 'start', '/welcome', 'welcome']:
                                response_message = get_welcome_message()
                            else:
                                # Check if this is a new user and send welcome
                                if send_welcome_to_new_user(sender):
                                    welcome_msg = get_welcome_message()
                                    # Send welcome message first
                                    whatsapp_url = f"https://graph.facebook.com/v22.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
                                    welcome_data = {
                                        "messaging_product": "whatsapp",
                                        "to": sender,
                                        "text": {"body": welcome_msg}
                                    }
                                    requests.post(
                                        whatsapp_url,
                                        headers={
                                            'Authorization': f'Bearer {os.getenv("WHATSAPP_API_TOKEN")}',
                                            'Content-Type': 'application/json'
                                        },
                                        json=welcome_data
                                    )
                                    # Add a small delay before processing the actual message
                                    time.sleep(1)

                                # Continue with normal processing (existing logic)
                                response_message = None  # Flag to continue with normal processing

                            # If we have a direct response message, send it and return
                            if response_message:
                                whatsapp_url = f"https://graph.facebook.com/v22.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
                                response_data = {
                                    "messaging_product": "whatsapp",
                                    "to": sender,
                                    "text": {"body": response_message}
                                }
                                send_response = requests.post(
                                    whatsapp_url,
                                    headers={
                                        'Authorization': f'Bearer {os.getenv("WHATSAPP_API_TOKEN")}',
                                        'Content-Type': 'application/json'
                                    },
                                    json=response_data
                                )
                                if send_response.status_code == 200:
                                    print(
                                        f"Info command response sent to {sender}")
                                    return jsonify({"status": "success"}), 200
                                else:
                                    print(
                                        f"Failed to send info response: {send_response.text}")
                                    return jsonify({"status": "error", "message": "Failed to send response"}), 500

                            # Check for language prefix
                            specified_language, cleaned_text, is_preference_setting, is_tts_request = extract_language_prefix(
                                text_content)

                            # If no language specified but user has a preference, use it
                            if not specified_language and not is_preference_setting and not is_tts_request:
                                user_preferred_language = user_language_preferences.get(
                                    sender)
                                print(
                                    f"Checking stored preferences for user {sender}: {user_preferred_language}")
                                print(
                                    f"All stored preferences: {user_language_preferences}")
                                if user_preferred_language:
                                    specified_language = user_preferred_language
                                    cleaned_text = text_content  # Use the entire text
                                    print(
                                        f"✅ Using stored language preference for user {sender}: {specified_language}")
                                else:
                                    print(
                                        f"❌ No stored language preference found for user {sender}")

                            print(f"🔍 Final processing parameters:")
                            print(
                                f"   - specified_language: {specified_language}")
                            print(f"   - cleaned_text: '{cleaned_text}'")
                            print(
                                f"   - is_preference_setting: {is_preference_setting}")
                            print(f"   - is_tts_request: {is_tts_request}")

                            # Handle TTS request
                            if is_tts_request:
                                if not cleaned_text:
                                    response_message = "Please provide text after the /speak command. Example: '/speak Báwo ni' (set your language preference first with /yoruba)"
                                else:
                                    # If no specific language was provided, use user's preference
                                    if not specified_language:
                                        user_preferred_language = user_language_preferences.get(
                                            sender)
                                        if user_preferred_language:
                                            specified_language = user_preferred_language
                                            print(
                                                f"Using user's language preference for TTS: {specified_language}")
                                        else:
                                            response_message = "Please set a language preference first using /yoruba, /igbo, /hausa, or /english, then try /speak again."
                                            # Send response and return early
                                            whatsapp_url = f"https://graph.facebook.com/v22.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
                                            response_data = {
                                                "messaging_product": "whatsapp",
                                                "to": sender,
                                                "text": {"body": response_message}
                                            }
                                            requests.post(whatsapp_url, headers={
                                                          'Authorization': f'Bearer {os.getenv("WHATSAPP_API_TOKEN")}', 'Content-Type': 'application/json'}, json=response_data)
                                            return jsonify({"status": "success"}), 200

                                    # Set up Spitch client
                                    spitch_api_key = os.getenv(
                                        "SPITCH_API_KEY")
                                    if not spitch_api_key:
                                        print(
                                            "SPITCH_API_KEY is not set in environment variables")
                                        return jsonify({"status": "error", "message": "Spitch API key not configured"}), 500

                                    # Set up Spitch client with environment variable
                                    os.environ["SPITCH_API_KEY"] = spitch_api_key
                                    client = Spitch()

                                    # Initialize audio_filename to prevent reference errors
                                    audio_filename = None

                                    # Generate speech
                                    result = generate_speech_audio(
                                        cleaned_text, specified_language, client)

                                    if result:
                                        audio_filename, content_type = result
                                        # Upload audio to WhatsApp and send
                                        try:
                                            # First, upload the media to WhatsApp
                                            upload_url = f"https://graph.facebook.com/v22.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/media"

                                            with open(audio_filename, 'rb') as audio_file:
                                                files = {
                                                    'file': (audio_filename, audio_file, content_type),
                                                }
                                                data = {
                                                    'type': 'audio',
                                                    'messaging_product': 'whatsapp'
                                                }
                                                headers = {
                                                    'Authorization': f'Bearer {os.getenv("WHATSAPP_API_TOKEN")}'
                                                }

                                                upload_response = requests.post(
                                                    upload_url, headers=headers, data=data, files=files)

                                                if upload_response.status_code == 200:
                                                    media_data = upload_response.json()
                                                    media_id = media_data['id']
                                                    print(
                                                        f"Audio uploaded successfully. Media ID: {media_id}")

                                                    # Send the audio message
                                                    whatsapp_url = f"https://graph.facebook.com/v22.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
                                                    response_data = {
                                                        "messaging_product": "whatsapp",
                                                        "to": sender,
                                                        "type": "audio",
                                                        "audio": {
                                                            "id": media_id
                                                        }
                                                    }

                                                    send_response = requests.post(
                                                        whatsapp_url,
                                                        headers={
                                                            'Authorization': f'Bearer {os.getenv("WHATSAPP_API_TOKEN")}',
                                                            'Content-Type': 'application/json'
                                                        },
                                                        json=response_data
                                                    )

                                                    if send_response.status_code == 200:
                                                        print(
                                                            "Audio message sent successfully via TTS")
                                                        # Clean up the temporary audio file
                                                        os.remove(
                                                            audio_filename)
                                                        return jsonify({"status": "success"}), 200
                                                    else:
                                                        print(
                                                            f"Failed to send audio message. Status: {send_response.status_code}")
                                                        print(
                                                            f"Response: {send_response.text}")
                                                        return jsonify({"status": "error", "message": "Failed to send audio message"}), 500
                                                else:
                                                    print(
                                                        f"Failed to upload audio. Status: {upload_response.status_code}")
                                                    print(
                                                        f"Response: {upload_response.text}")
                                                    return jsonify({"status": "error", "message": "Failed to upload audio"}), 500

                                        except Exception as upload_error:
                                            print(
                                                f"Error uploading/sending audio: {str(upload_error)}")
                                            return jsonify({"status": "error", "message": f"Upload error: {str(upload_error)}"}), 500
                                        finally:
                                            # Clean up the temporary audio file with better error handling
                                            if audio_filename and os.path.exists(audio_filename):
                                                try:
                                                    os.remove(audio_filename)
                                                    print(
                                                        f"Cleaned up audio file: {audio_filename}")
                                                except Exception as cleanup_error:
                                                    print(
                                                        f"Warning: Could not clean up audio file {audio_filename}: {str(cleanup_error)}")
                                    else:
                                        response_message = "Failed to convert speech to WhatsApp-compatible audio format. Please ensure ffmpeg is installed on the system."

                                # Send text response if not sending audio
                                if not (is_tts_request and cleaned_text and audio_filename):
                                    whatsapp_url = f"https://graph.facebook.com/v22.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
                                    response_data = {
                                        "messaging_product": "whatsapp",
                                        "to": sender,
                                        "text": {
                                            "body": response_message
                                        }
                                    }
                                    send_response = requests.post(
                                        whatsapp_url,
                                        headers={
                                            'Authorization': f'Bearer {os.getenv("WHATSAPP_API_TOKEN")}',
                                            'Content-Type': 'application/json'
                                        },
                                        json=response_data
                                    )
                                    return jsonify({"status": "success"}), 200

                            # If this is just a language preference setting (e.g., "/igbo")
                            if is_preference_setting and specified_language:
                                user_language_preferences[sender] = specified_language
                                save_user_preferences(
                                    user_language_preferences)  # Persist to file
                                language_names = {
                                    'yo': 'Yoruba',
                                    'ig': 'Igbo',
                                    'ha': 'Hausa',
                                    'en': 'English'
                                }
                                response_message = f"Language preference set to {language_names[specified_language]}. Your next text and audio messages will be processed in {language_names[specified_language]}."
                                print(
                                    f"Language preference saved for user {sender}: {language_names[specified_language]}")

                                # Send response via WhatsApp
                                whatsapp_url = f"https://graph.facebook.com/v22.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
                                response_data = {
                                    "messaging_product": "whatsapp",
                                    "to": sender,
                                    "text": {
                                        "body": response_message
                                    }
                                }
                                send_response = requests.post(
                                    whatsapp_url,
                                    headers={
                                        'Authorization': f'Bearer {os.getenv("WHATSAPP_API_TOKEN")}',
                                        'Content-Type': 'application/json'
                                    },
                                    json=response_data
                                )

                                if send_response.status_code == 200:
                                    print(
                                        f"Language preference set for user {sender}: {language_names[specified_language]}")
                                    return jsonify({"status": "success"}), 200
                                else:
                                    print(
                                        f"Failed to send WhatsApp response. Status: {send_response.status_code}")
                                    print(f"Response: {send_response.text}")
                                    print(f"Request URL: {whatsapp_url}")
                                    print(f"Request data: {response_data}")
                                    print(
                                        f"Request headers: Authorization: Bearer {os.getenv('WHATSAPP_API_TOKEN')[:20]}...")
                                    return jsonify({"status": "error", "message": "Failed to send WhatsApp response"}), 500

                            # Set up Spitch client for translation
                            spitch_api_key = os.getenv("SPITCH_API_KEY")
                            print(
                                f"Text translation - Spitch API Key present: {'Yes' if spitch_api_key else 'No'}")
                            if not spitch_api_key:
                                print(
                                    "SPITCH_API_KEY is not set in environment variables")
                                return jsonify({"status": "error", "message": "Spitch API key not configured"}), 500

                            # Initialize Spitch client with environment variable
                            try:
                                # Set the API key in environment (required by Spitch SDK)
                                os.environ["SPITCH_API_KEY"] = spitch_api_key
                                client = Spitch()
                                print(
                                    "Text translation - Spitch client initialized successfully")
                            except Exception as client_error:
                                print(
                                    f"Failed to initialize Spitch client: {str(client_error)}")
                                return jsonify({"status": "error", "message": f"Spitch client initialization failed: {str(client_error)}"}), 500

                            language_names = {
                                'yo': 'Yoruba',
                                'ig': 'Igbo',
                                'ha': 'Hausa',
                                'en': 'English'
                            }

                            response_message = f"Text: {cleaned_text}"

                            if specified_language:
                                # User specified a language, translate directly
                                try:
                                    print(
                                        f"User specified {language_names[specified_language]}, translating to English...")
                                    print(f"Source text: '{cleaned_text}'")
                                    print(
                                        f"Source language: {specified_language}")
                                    print(f"Target language: en")

                                    translation_response = client.text.translate(
                                        text=cleaned_text,
                                        source=specified_language,
                                        target="en"
                                    )
                                    print(f"Translation API response received")
                                    english_translation = translation_response.text.strip()
                                    print(
                                        f"Translation result: '{english_translation}'")

                                    if english_translation:
                                        # Enhance text with diacritics based on language
                                        display_text = cleaned_text
                                        if specified_language == 'ig':
                                            display_text = enhance_igbo_text_with_diacritics(
                                                cleaned_text)
                                            print(
                                                f"Enhanced Igbo text: '{display_text}'")
                                        elif specified_language == 'yo':
                                            display_text = enhance_yoruba_text_with_diacritics(
                                                cleaned_text)
                                            print(
                                                f"Enhanced Yoruba text: '{display_text}'")

                                        response_message = f"Text ({language_names[specified_language]}): {display_text}\n\nEnglish translation: {english_translation}"
                                        print(
                                            f"Translation from {language_names[specified_language]}: {english_translation}")
                                    else:
                                        print(
                                            "Translation returned empty result")
                                        response_message = f"Text ({language_names[specified_language]}): {cleaned_text}\n\nTranslation failed: Empty result"

                                except Exception as translation_error:
                                    print(
                                        f"Translation from {language_names[specified_language]} failed: {str(translation_error)}")
                                    print(
                                        f"Error type: {type(translation_error).__name__}")
                                    import traceback
                                    print(
                                        f"Full traceback: {traceback.format_exc()}")
                                    response_message = f"Text ({language_names[specified_language]}): {cleaned_text}\n\nTranslation error: {str(translation_error)}"
                            else:
                                # Auto-detect language and translate to English if needed
                                # Try to detect if the text is in an African language
                                # Yoruba, Igbo, Hausa
                                languages_to_try = ['yo', 'ig', 'ha']

                                # Try to translate from each African language to English
                                translation_found = False
                                print(
                                    f"Auto-detecting language for text: '{cleaned_text}'")
                                for lang_code in languages_to_try:
                                    try:
                                        print(
                                            f"Trying translation from {language_names[lang_code]} to English...")
                                        translation_response = client.text.translate(
                                            text=cleaned_text,
                                            source=lang_code,
                                            target="en"
                                        )
                                        english_translation = translation_response.text.strip()
                                        print(
                                            f"  {language_names[lang_code]} result: '{english_translation}'")

                                        # If translation is significantly different from original, it's likely correct
                                        if english_translation and english_translation.lower() != cleaned_text.lower():
                                            # Enhance text with diacritics based on detected language
                                            display_text = cleaned_text
                                            if lang_code == 'ig':
                                                display_text = enhance_igbo_text_with_diacritics(
                                                    cleaned_text)
                                                print(
                                                    f"Enhanced Igbo text in auto-detection: '{display_text}'")
                                            elif lang_code == 'yo':
                                                display_text = enhance_yoruba_text_with_diacritics(
                                                    cleaned_text)
                                                print(
                                                    f"Enhanced Yoruba text in auto-detection: '{display_text}'")

                                            response_message = f"Text ({language_names[lang_code]}): {display_text}\n\nEnglish translation: {english_translation}"
                                            print(
                                                f"Translation from {language_names[lang_code]}: {english_translation}")
                                            translation_found = True
                                            break
                                        else:
                                            print(
                                                f"  {language_names[lang_code]}: Translation same as original, trying next language")

                                    except Exception as translation_error:
                                        print(
                                            f"Translation from {language_names[lang_code]} failed: {str(translation_error)}")
                                        print(
                                            f"  Error type: {type(translation_error).__name__}")
                                        continue

                                # If no translation was found, assume it's already in English
                                if not translation_found:
                                    response_message = f"Text (English): {cleaned_text}"
                                    print(
                                        "Text appears to be in English, no translation needed")

                            # Send response via WhatsApp
                            whatsapp_url = f"https://graph.facebook.com/v22.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
                            response_data = {
                                "messaging_product": "whatsapp",
                                "to": sender,
                                "text": {
                                    "body": response_message
                                }
                            }
                            send_response = requests.post(
                                whatsapp_url,
                                headers={
                                    'Authorization': f'Bearer {os.getenv("WHATSAPP_API_TOKEN")}',
                                    'Content-Type': 'application/json'
                                },
                                json=response_data
                            )

                            if send_response.status_code != 200:
                                print(
                                    f"Failed to send WhatsApp response. Status: {send_response.status_code}")
                                print(f"Response: {send_response.text}")
                                return jsonify({"status": "error", "message": "Failed to send WhatsApp response"}), 500

                            print("Successfully processed text and sent response")
                            return jsonify({"status": "success"}), 200

                        except Exception as e:
                            print(f"Error processing text message: {str(e)}")
                            return jsonify({"status": "error", "message": str(e)}), 500

            return jsonify({"status": "no audio or text found"}), 200

        except Exception as e:
            print(f"Error processing webhook: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    print("🤖 Spitch Translator Bot Starting...")
    print("=" * 50)
    print("Available Commands:")
    print("• /help - Show detailed help")
    print("• /commands - Show quick commands")
    print("• /yoruba, /igbo, /hausa, /english - Set language preference")
    print("• Send voice notes or text for translation")
    print("=" * 50)

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
