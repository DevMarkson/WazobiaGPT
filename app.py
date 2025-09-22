from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import json
from spitch import Spitch
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Simple in-memory cache to track processed messages with timestamps
processed_messages = {}

# Store user language preferences (user_id -> language_code)
user_language_preferences = {}


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
    """Extract language prefix from text and return (language_code, cleaned_text, is_preference_setting)"""
    language_prefixes = {
        '/yoruba': 'yo',
        '/igbo': 'ig',
        '/hausa': 'ha',
        '/english': 'en'
    }

    text_lower = text.lower().strip()
    for prefix, lang_code in language_prefixes.items():
        if text_lower.startswith(prefix):
            # Remove the prefix and any whitespace after it
            cleaned_text = text[len(prefix):].strip()

            # If there's no text after the prefix, it's a preference setting
            is_preference_setting = len(cleaned_text) == 0

            return lang_code, cleaned_text, is_preference_setting

    return None, text, False


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

                            # Save the audio file
                            audio_file = 'voice_note.ogg'
                            with open(audio_file, 'wb') as f:
                                f.write(download_response.content)
                            print("Audio file saved successfully")

                            # Transcribe with Spitch SDK
                            try:
                                # Set up Spitch client
                                spitch_api_key = os.getenv("SPITCH_API_KEY")
                                if not spitch_api_key:
                                    print(
                                        "SPITCH_API_KEY is not set in environment variables")
                                    return jsonify({"status": "error", "message": "Spitch API key not configured"}), 500

                                # Set the API key in environment (required by Spitch SDK)
                                os.environ["SPITCH_API_KEY"] = spitch_api_key
                                client = Spitch()

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
                                    "body": f"Transcription: {transcription}"
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

                            # Check for language prefix
                            specified_language, cleaned_text, is_preference_setting = extract_language_prefix(
                                text_content)

                            # If this is just a language preference setting (e.g., "/igbo")
                            if is_preference_setting and specified_language:
                                user_language_preferences[sender] = specified_language
                                language_names = {
                                    'yo': 'Yoruba',
                                    'ig': 'Igbo',
                                    'ha': 'Hausa',
                                    'en': 'English'
                                }
                                response_message = f"Language preference set to {language_names[specified_language]}. Your next audio messages will be transcribed in {language_names[specified_language]}."

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
                                    print(f"Response: {send_response.text}")
                                    print(f"Request URL: {whatsapp_url}")
                                    print(f"Request data: {response_data}")
                                    print(
                                        f"Request headers: Authorization: Bearer {os.getenv('WHATSAPP_API_TOKEN')[:20]}...")
                                    return jsonify({"status": "error", "message": "Failed to send WhatsApp response"}), 500
                                    print(
                                        f"Failed to send WhatsApp response. Status: {send_response.status_code}")

                            # Set up Spitch client for translation
                            spitch_api_key = os.getenv("SPITCH_API_KEY")
                            if not spitch_api_key:
                                print(
                                    "SPITCH_API_KEY is not set in environment variables")
                                return jsonify({"status": "error", "message": "Spitch API key not configured"}), 500

                            # Set the API key in environment (required by Spitch SDK)
                            os.environ["SPITCH_API_KEY"] = spitch_api_key
                            client = Spitch()

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
                                    translation_response = client.text.translate(
                                        text=cleaned_text,
                                        source=specified_language,
                                        target="en"
                                    )
                                    english_translation = translation_response.text.strip()

                                    if english_translation:
                                        response_message = f"Text ({language_names[specified_language]}): {cleaned_text}\n\nEnglish translation: {english_translation}"
                                        print(
                                            f"Translation from {language_names[specified_language]}: {english_translation}")
                                    else:
                                        response_message = f"Text ({language_names[specified_language]}): {cleaned_text}\n\nTranslation failed"

                                except Exception as translation_error:
                                    print(
                                        f"Translation from {language_names[specified_language]} failed: {str(translation_error)}")
                                    response_message = f"Text ({language_names[specified_language]}): {cleaned_text}\n\nTranslation error: {str(translation_error)}"
                            else:
                                # Auto-detect language and translate to English if needed
                                # Try to detect if the text is in an African language
                                # Yoruba, Igbo, Hausa
                                languages_to_try = ['yo', 'ig', 'ha']

                                # Try to translate from each African language to English
                                translation_found = False
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

                                        # If translation is significantly different from original, it's likely correct
                                        if english_translation and english_translation.lower() != cleaned_text.lower():
                                            response_message = f"Text ({language_names[lang_code]}): {cleaned_text}\n\nEnglish translation: {english_translation}"
                                            print(
                                                f"Translation from {language_names[lang_code]}: {english_translation}")
                                            translation_found = True
                                            break

                                    except Exception as translation_error:
                                        print(
                                            f"Translation from {language_names[lang_code]} failed: {str(translation_error)}")
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
    app.run(port=5000, debug=True)
