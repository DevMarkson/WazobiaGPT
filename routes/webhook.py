import os
import time
import traceback
from flask import Blueprint, request, jsonify

from config import (
    WEBHOOK_VERIFY_TOKEN,
    WHATSAPP_API_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    SPITCH_API_KEY,
    LANGUAGE_NAMES,
    REQUIRED_ENV_VARS
)
from utils.messages import (
    get_welcome_message,
    get_help_message,
    get_commands_list,
    get_status_message
)
from services.storage import (
    get_all_preferences,
    get_user_preference,
    set_user_preference,
    clear_user_preference,
    send_welcome_to_new_user,
    is_message_processed,
    mark_message_processed,
    maybe_cleanup_processed_messages
)
from services.text_service import (
    extract_language_prefix,
    enhance_text_by_language,
    enhance_igbo_text_with_diacritics,
    enhance_yoruba_text_with_diacritics
)
from services.spitch_service import (
    get_spitch_client,
    translate_text,
    generate_speech_audio,
    transcribe_and_translate_audio
)
from services.whatsapp_service import (
    send_whatsapp_text,
    send_whatsapp_audio,
    get_media_url,
    download_media_file,
    upload_audio_media
)

webhook_bp = Blueprint('webhook', __name__)


@webhook_bp.route('/debug-preferences', methods=['GET'])
def debug_preferences():
    """Debug endpoint to check user language preferences"""
    preferences = get_all_preferences()
    return jsonify({
        "status": "success",
        "user_preferences": preferences,
        "total_users": len(preferences)
    }), 200


@webhook_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    env_status = {}
    for var in REQUIRED_ENV_VARS:
        env_status[var] = "Present" if os.getenv(var) else "Missing"

    return jsonify({
        "status": "healthy",
        "environment_variables": env_status,
        "timestamp": time.time()
    }), 200


@webhook_bp.route('/test-spitch', methods=['GET'])
def test_spitch():
    """Test endpoint to verify Spitch API is working"""
    try:
        client = get_spitch_client()
        if not client:
            return jsonify({"status": "error", "message": "SPITCH_API_KEY not set"}), 500

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


@webhook_bp.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        verify_token = WEBHOOK_VERIFY_TOKEN or os.getenv('WEBHOOK_VERIFY_TOKEN')
        if request.args.get('hub.verify_token') == verify_token:
            return request.args.get('hub.challenge'), 200
        return 'Forbidden', 403

    elif request.method == 'POST':
        try:
            data = request.json
            print("Received webhook data:", data)

            if ('entry' in data and len(data['entry']) > 0 and
                'changes' in data['entry'][0] and len(data['entry'][0]['changes']) > 0 and
                'value' in data['entry'][0]['changes'][0] and
                'messages' in data['entry'][0]['changes'][0]['value']):

                messages = data['entry'][0]['changes'][0]['value']['messages']
                for message in messages:
                    if message.get('type') == 'audio':
                        return _handle_audio_message(message)
                    elif message.get('type') == 'text':
                        return _handle_text_message(message)

            return jsonify({"status": "no audio or text found"}), 200

        except Exception as e:
            print(f"Error processing webhook: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500


def _handle_audio_message(message):
    try:
        maybe_cleanup_processed_messages()

        media_id = message['audio']['id']
        sender = message['from']
        message_id = message['id']

        if is_message_processed(message_id):
            print(f"Message {message_id} already processed, skipping...")
            return jsonify({"status": "already processed"}), 200

        mark_message_processed(message_id)
        print(f"Processing audio message {media_id} from {sender} (message_id: {message_id})")

        download_url, media_info_res = get_media_url(media_id)
        if not download_url:
            error_msg = "Failed to get media URL"
            try:
                error_data = media_info_res.json()
                error_msg = error_data.get('error', {}).get('message', error_msg)
            except Exception:
                pass
            return jsonify({"status": "error", "message": error_msg}), 500

        audio_file, download_res = download_media_file(download_url)
        if not audio_file:
            return jsonify({"status": "error", "message": "Failed to download audio"}), 500

        user_preferred_language = get_user_preference(sender)
        transcription_result, error_msg, status_code = transcribe_and_translate_audio(
            audio_file, user_preferred_language
        )

        # Clean up temporary downloaded file
        if os.path.exists(audio_file):
            try:
                os.remove(audio_file)
                print(f"Cleaned up audio file: {audio_file}")
            except Exception as cleanup_error:
                print(f"Warning: Could not clean up audio file {audio_file}: {cleanup_error}")

        if error_msg:
            return jsonify({"status": "error", "message": error_msg}), status_code

        send_res = send_whatsapp_text(sender, transcription_result)
        if send_res.status_code != 200:
            return jsonify({"status": "error", "message": "Failed to send WhatsApp response"}), 500

        print("Successfully processed audio and sent response")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"Error processing audio message: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


def _handle_text_message(message):
    try:
        maybe_cleanup_processed_messages()

        text_content = message['text']['body']
        sender = message['from']
        message_id = message['id']

        if is_message_processed(message_id):
            print(f"Text message {message_id} already processed, skipping...")
            return jsonify({"status": "already processed"}), 200

        mark_message_processed(message_id)
        print(f"Processing text message from {sender} (message_id: {message_id}): '{text_content}'")

        text_lower = text_content.lower().strip()

        # Handle command routing
        if text_lower in ['/help', 'help', '/h']:
            response_message = get_help_message()
        elif text_lower in ['/commands', '/cmd', 'commands']:
            response_message = get_commands_list()
        elif text_lower in ['/status', 'status']:
            response_message = get_status_message(sender, get_user_preference(sender))
        elif text_lower in ['/reset', 'reset']:
            if clear_user_preference(sender):
                response_message = "✅ Language preference cleared! I'll now auto-detect languages for your messages.\n\nTo set a new preference, use:\n/yoruba /igbo /hausa /english"
            else:
                response_message = "ℹ️ You don't have any language preference set. Use /help to see available commands."
        elif text_lower in ['/start', 'start', '/welcome', 'welcome']:
            response_message = get_welcome_message()
        else:
            # Check if this is a new user and greet them
            if send_welcome_to_new_user(sender):
                welcome_msg = get_welcome_message()
                send_whatsapp_text(sender, welcome_msg)
                time.sleep(1)

            response_message = None

        if response_message:
            send_res = send_whatsapp_text(sender, response_message)
            if send_res.status_code == 200:
                print(f"Info command response sent to {sender}")
                return jsonify({"status": "success"}), 200
            else:
                print(f"Failed to send info response: {send_res.text}")
                return jsonify({"status": "error", "message": "Failed to send response"}), 500

        # Check for language prefixes or /speak commands
        specified_language, cleaned_text, is_preference_setting, is_tts_request = extract_language_prefix(text_content)

        if not specified_language and not is_preference_setting and not is_tts_request:
            user_pref = get_user_preference(sender)
            print(f"Checking stored preferences for user {sender}: {user_pref}")
            if user_pref:
                specified_language = user_pref
                cleaned_text = text_content
                print(f"✅ Using stored language preference for user {sender}: {specified_language}")
            else:
                print(f"❌ No stored language preference found for user {sender}")

        # Handle TTS requests (/speak)
        if is_tts_request:
            return _handle_tts_request(sender, cleaned_text, specified_language)

        # Handle preference configuration (e.g., /igbo)
        if is_preference_setting and specified_language:
            set_user_preference(sender, specified_language)
            lang_label = LANGUAGE_NAMES.get(specified_language, specified_language)
            response_msg = f"Language preference set to {lang_label}. Your next text and audio messages will be processed in {lang_label}."
            print(f"Language preference saved for user {sender}: {lang_label}")
            send_res = send_whatsapp_text(sender, response_msg)
            if send_res.status_code == 200:
                return jsonify({"status": "success"}), 200
            else:
                return jsonify({"status": "error", "message": "Failed to send WhatsApp response"}), 500

        # Handle text translation
        return _handle_text_translation(sender, cleaned_text, specified_language)

    except Exception as e:
        print(f"Error processing text message: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


def _handle_tts_request(sender, cleaned_text, specified_language):
    """Handle text-to-speech generation and delivery"""
    if not cleaned_text:
        msg = "Please provide text after the /speak command. Example: '/speak Báwo ni' (set your language preference first with /yoruba)"
        send_whatsapp_text(sender, msg)
        return jsonify({"status": "success"}), 200

    if not specified_language:
        user_pref = get_user_preference(sender)
        if user_pref:
            specified_language = user_pref
            print(f"Using user's language preference for TTS: {specified_language}")
        else:
            msg = "Please set a language preference first using /yoruba, /igbo, /hausa, or /english, then try /speak again."
            send_whatsapp_text(sender, msg)
            return jsonify({"status": "success"}), 200

    audio_filename, content_type = generate_speech_audio(cleaned_text, specified_language)
    if not audio_filename:
        msg = "Failed to convert speech to WhatsApp-compatible audio format. Please ensure ffmpeg is installed on the system."
        send_whatsapp_text(sender, msg)
        return jsonify({"status": "success"}), 200

    try:
        media_id, upload_res = upload_audio_media(audio_filename, content_type)
        if not media_id:
            return jsonify({"status": "error", "message": "Failed to upload audio"}), 500

        send_res = send_whatsapp_audio(sender, media_id)
        if send_res.status_code == 200:
            print("Audio message sent successfully via TTS")
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to send audio message"}), 500

    except Exception as upload_error:
        print(f"Error uploading/sending audio: {str(upload_error)}")
        return jsonify({"status": "error", "message": f"Upload error: {str(upload_error)}"}), 500
    finally:
        if audio_filename and os.path.exists(audio_filename):
            try:
                os.remove(audio_filename)
                print(f"Cleaned up audio file: {audio_filename}")
            except Exception as cleanup_error:
                print(f"Warning: Could not clean up audio file {audio_filename}: {cleanup_error}")


def _handle_text_translation(sender, cleaned_text, specified_language):
    """Handle text translation when user sends text"""
    client = get_spitch_client()
    if not client:
        return jsonify({"status": "error", "message": "Spitch API key not configured"}), 500

    response_message = f"Text: {cleaned_text}"

    if specified_language:
        lang_label = LANGUAGE_NAMES.get(specified_language, specified_language)
        try:
            print(f"User specified {lang_label}, translating to English...")
            english_translation = translate_text(
                text=cleaned_text,
                source_lang=specified_language,
                target_lang="en"
            )

            if english_translation:
                display_text = enhance_text_by_language(cleaned_text, specified_language)
                response_message = f"Text ({lang_label}): {display_text}\n\nEnglish translation: {english_translation}"
            else:
                response_message = f"Text ({lang_label}): {cleaned_text}\n\nTranslation failed: Empty result"

        except Exception as translation_error:
            print(f"Translation from {lang_label} failed: {str(translation_error)}")
            print(f"Full traceback: {traceback.format_exc()}")
            response_message = f"Text ({lang_label}): {cleaned_text}\n\nTranslation error: {str(translation_error)}"
    else:
        # Auto-detect language across Nigerian languages
        languages_to_try = ['yo', 'ig', 'ha']
        translation_found = False
        print(f"Auto-detecting language for text: '{cleaned_text}'")

        for lang_code in languages_to_try:
            lang_label = LANGUAGE_NAMES.get(lang_code, lang_code)
            try:
                print(f"Trying translation from {lang_label} to English...")
                english_translation = translate_text(
                    text=cleaned_text,
                    source_lang=lang_code,
                    target_lang="en"
                )

                if english_translation and english_translation.lower() != cleaned_text.lower():
                    display_text = enhance_text_by_language(cleaned_text, lang_code)
                    response_message = f"Text ({lang_label}): {display_text}\n\nEnglish translation: {english_translation}"
                    print(f"Translation from {lang_label}: {english_translation}")
                    translation_found = True
                    break
                else:
                    print(f"  {lang_label}: Translation same as original, trying next language")
            except Exception as translation_error:
                print(f"Translation from {lang_label} failed: {str(translation_error)}")
                continue

        if not translation_found:
            response_message = f"Text (English): {cleaned_text}"
            print("Text appears to be in English, no translation needed")

    send_res = send_whatsapp_text(sender, response_message)
    if send_res.status_code != 200:
        return jsonify({"status": "error", "message": "Failed to send WhatsApp response"}), 500

    print("Successfully processed text and sent response")
    return jsonify({"status": "success"}), 200
