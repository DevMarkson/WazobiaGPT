#!/usr/bin/env python3
"""
Test the language preference and translation logic locally
"""

import sys
import os
sys.path.append('.')

# Mock the extract_language_prefix function and user_language_preferences


def extract_language_prefix(text):
    """Extract language prefix from text and return (language_code, cleaned_text, is_preference_setting, is_tts_request)"""
    language_prefixes = {
        '/yoruba': 'yo',
        '/igbo': 'ig',
        '/hausa': 'ha',
        '/english': 'en'
    }

    # Check for TTS commands first
    tts_commands = ['/tts', '/speak']
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

            # No specific language mentioned, default to English for TTS
            return 'en', remaining_text, False, True

    # Check for regular language prefixes (for transcription/translation)
    for prefix, lang_code in language_prefixes.items():
        if text_lower.startswith(prefix):
            # Remove the prefix and any whitespace after it
            cleaned_text = text[len(prefix):].strip()

            # If there's no text after the prefix, it's a preference setting
            is_preference_setting = len(cleaned_text) == 0

            return lang_code, cleaned_text, is_preference_setting, False

    return None, text, False, False


def test_language_logic():
    """Test the language preference logic"""
    print("Testing language preference logic...")

    # Simulate user language preferences (like in the app)
    user_language_preferences = {}
    sender = "test_user"

    # Test 1: Setting language preference
    print("\n--- Test 1: Setting language preference ---")
    text_content = "/igbo"
    specified_language, cleaned_text, is_preference_setting, is_tts_request = extract_language_prefix(
        text_content)

    print(f"Input: '{text_content}'")
    print(f"specified_language: {specified_language}")
    print(f"cleaned_text: '{cleaned_text}'")
    print(f"is_preference_setting: {is_preference_setting}")
    print(f"is_tts_request: {is_tts_request}")

    if is_preference_setting and specified_language:
        user_language_preferences[sender] = specified_language
        print(f"✅ Language preference set for {sender}: {specified_language}")

    # Test 2: Using stored preference for regular text
    print("\n--- Test 2: Using stored preference for regular text ---")
    text_content = "Ndewo"  # Hello in Igbo
    specified_language, cleaned_text, is_preference_setting, is_tts_request = extract_language_prefix(
        text_content)

    print(f"Input: '{text_content}'")
    print(f"specified_language (initial): {specified_language}")
    print(f"cleaned_text (initial): '{cleaned_text}'")
    print(f"is_preference_setting: {is_preference_setting}")
    print(f"is_tts_request: {is_tts_request}")

    # Apply the new logic
    if not specified_language and not is_preference_setting and not is_tts_request:
        user_preferred_language = user_language_preferences.get(sender)
        if user_preferred_language:
            specified_language = user_preferred_language
            cleaned_text = text_content  # Use the entire text
            print(
                f"✅ Using stored language preference for user {sender}: {specified_language}")

    print(f"specified_language (final): {specified_language}")
    print(f"cleaned_text (final): '{cleaned_text}'")

    # Test 3: Explicit language override
    print("\n--- Test 3: Explicit language override ---")
    text_content = "/yoruba Bawo ni"
    specified_language, cleaned_text, is_preference_setting, is_tts_request = extract_language_prefix(
        text_content)

    print(f"Input: '{text_content}'")
    print(f"specified_language: {specified_language}")
    print(f"cleaned_text: '{cleaned_text}'")
    print(f"is_preference_setting: {is_preference_setting}")
    print(f"is_tts_request: {is_tts_request}")

    if specified_language:
        print(f"✅ Explicit language specified: {specified_language}")

    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    test_language_logic()
