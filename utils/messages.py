from config import LANGUAGE_NAMES


def get_welcome_message():
    """Generate welcome message for new users"""
    return """🤖 Welcome to WazobiaGPT! 

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

 TEXT-TO-SPEECH:
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


def get_status_message(sender, user_preference=None):
    """Generate user status message"""
    if user_preference:
        lang_name = LANGUAGE_NAMES.get(user_preference, 'Unknown')
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
