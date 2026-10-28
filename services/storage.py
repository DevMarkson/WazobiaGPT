import json
import os
import time
from config import PREFERENCES_FILE, WELCOMED_FILE

# In-memory cache to track processed messages with timestamps
processed_messages = {}


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
        if os.path.exists(WELCOMED_FILE):
            with open(WELCOMED_FILE, 'r') as f:
                welcomed = json.load(f)
                print(f"Loaded {len(welcomed)} welcomed users from file")
                return set(welcomed)
    except Exception as e:
        print(f"Error loading welcomed users: {e}")
    return set()


def save_welcomed_users(welcomed_users_set):
    """Save list of welcomed users to file"""
    try:
        with open(WELCOMED_FILE, 'w') as f:
            json.dump(list(welcomed_users_set), f)
            print(f"Saved {len(welcomed_users_set)} welcomed users to file")
    except Exception as e:
        print(f"Error saving welcomed users: {e}")


# Initialize in-memory state from storage
user_language_preferences = load_user_preferences()
welcomed_users = load_welcomed_users()


def get_user_preference(sender):
    """Get the preferred language for a user"""
    return user_language_preferences.get(sender)


def set_user_preference(sender, language_code):
    """Set and persist a user's language preference"""
    user_language_preferences[sender] = language_code
    save_user_preferences(user_language_preferences)


def clear_user_preference(sender):
    """Clear a user's language preference"""
    if sender in user_language_preferences:
        del user_language_preferences[sender]
        save_user_preferences(user_language_preferences)
        return True
    return False


def get_all_preferences():
    """Get a copy of all user preferences"""
    return dict(user_language_preferences)


def send_welcome_to_new_user(sender):
    """Check if user has been welcomed before; if not, mark welcomed and return True"""
    if sender not in welcomed_users:
        welcomed_users.add(sender)
        save_welcomed_users(welcomed_users)
        return True
    return False


def is_message_processed(message_id):
    """Check if message has already been processed"""
    return message_id in processed_messages


def mark_message_processed(message_id):
    """Mark a message as processed with current timestamp"""
    processed_messages[message_id] = time.time()


def cleanup_old_messages():
    """Remove messages older than 1 hour from the cache"""
    current_time = time.time()
    one_hour_ago = current_time - 3600  # 3600 seconds = 1 hour

    messages_to_remove = [
        msg_id for msg_id, timestamp in processed_messages.items()
        if timestamp < one_hour_ago
    ]

    for message_id in messages_to_remove:
        del processed_messages[message_id]

    print(f"Cleaned up {len(messages_to_remove)} old messages from cache")


def maybe_cleanup_processed_messages():
    """Trigger cleanup if processed messages cache exceeds 100 entries"""
    if len(processed_messages) > 100:
        cleanup_old_messages()
