import os
import time
from spitch import Spitch
from config import SPITCH_API_KEY, VOICE_MAPPING, LANGUAGE_NAMES
from services.audio_service import convert_wav_to_compatible_format, is_low_quality_transcription


def get_spitch_client():
    """Get an initialized Spitch client instance"""
    api_key = SPITCH_API_KEY or os.getenv("SPITCH_API_KEY")
    if not api_key:
        return None
    os.environ["SPITCH_API_KEY"] = api_key
    return Spitch()


def translate_text(text, source_lang, target_lang="en"):
    """Translate text from source language to target language using Spitch"""
    client = get_spitch_client()
    if not client:
        raise ValueError("SPITCH_API_KEY is not configured")

    response = client.text.translate(
        text=text,
        source=source_lang,
        target=target_lang
    )
    return response.text.strip() if response and response.text else ""


def generate_speech_audio(text, language_code):
    """Generate speech audio using Spitch API and convert to MP3/compatible format"""
    client = get_spitch_client()
    if not client:
        print("SPITCH_API_KEY is not set in environment variables")
        return None, None

    voice = VOICE_MAPPING.get(language_code, 'lucy')

    try:
        print(f"Generating speech for text: '{text}' in language: {language_code} with voice: {voice}")

        response = client.speech.generate(
            text=text,
            language=language_code,
            voice=voice
        )

        temp_wav_filename = f"temp_tts_{int(time.time())}.wav"
        with open(temp_wav_filename, "wb") as f:
            f.write(response.read())

        converted_filename, content_type = convert_wav_to_compatible_format(temp_wav_filename)

        # Clean up temporary WAV file
        if os.path.exists(temp_wav_filename):
            try:
                os.remove(temp_wav_filename)
            except Exception as cleanup_error:
                print(f"Warning: Could not remove temp file {temp_wav_filename}: {cleanup_error}")

        if converted_filename and os.path.exists(converted_filename):
            print(f"Speech generated and converted successfully: {converted_filename}")
            return converted_filename, content_type
        else:
            print("Failed to convert audio to WhatsApp-compatible format")
            return None, None

    except Exception as e:
        print(f"Error generating speech: {str(e)}")
        return None, None


def transcribe_and_translate_audio(audio_file_path, user_preferred_language=None):
    """
    Transcribe audio file using Spitch, attempting preferred language first,
    falling back across Nigerian languages and English, and translating non-English to English.

    Returns:
        tuple: (response_message, error_message, status_code)
    """
    client = get_spitch_client()
    if not client:
        return None, "Spitch API key not configured", 500

    try:
        with open(audio_file_path, "rb") as f:
            audio_content = f.read()
            print(f"Transcribing audio file: {audio_file_path}")

        languages_to_try = ['yo', 'ig', 'ha', 'en']
        best_transcription = ""
        detected_language = ""
        best_confidence = 0

        # Try user's preferred language first if set
        if user_preferred_language:
            lang_label = LANGUAGE_NAMES.get(user_preferred_language, user_preferred_language)
            print(f"Using user's preferred language: {lang_label} ({user_preferred_language})")
            try:
                response = client.speech.transcribe(
                    language=user_preferred_language,
                    content=audio_content
                )
                transcription = response.text.strip() if response and response.text else ""

                if transcription:
                    if not is_low_quality_transcription(transcription):
                        best_transcription = transcription
                        detected_language = user_preferred_language
                        best_confidence = len(transcription.split())
                        print(f"Transcription with preferred language: '{transcription}'")
                    else:
                        print("Low quality transcription detected with preferred language")
            except Exception as lang_error:
                print(f"Error transcribing with preferred language {lang_label}: {str(lang_error)}")

        # If no preferred language or transcription failed, try all languages
        if not best_transcription:
            for lang_code in languages_to_try:
                try:
                    lang_label = LANGUAGE_NAMES.get(lang_code, lang_code)
                    print(f"Trying transcription with language: {lang_label} ({lang_code})")
                    response = client.speech.transcribe(
                        language=lang_code,
                        content=audio_content
                    )
                    transcription = response.text.strip() if response and response.text else ""

                    if transcription:
                        if is_low_quality_transcription(transcription):
                            print(f"  {lang_label}: Low quality transcription detected, skipping")
                            continue

                        confidence = len(transcription.split())
                        print(f"  {lang_label}: '{transcription}' (confidence: {confidence})")

                        if confidence > best_confidence:
                            best_transcription = transcription
                            detected_language = lang_code
                            best_confidence = confidence
                except Exception as lang_error:
                    print(f"  Error with {LANGUAGE_NAMES.get(lang_code, lang_code)}: {str(lang_error)}")
                    continue

        if not best_transcription:
            print("No successful transcription from any language")
            return None, "No transcription result", 500

        # Final quality check
        if is_low_quality_transcription(best_transcription):
            print(f"Best transcription failed quality check: '{best_transcription[:100]}...'")
            return None, "Audio quality too poor for transcription", 400

        detected_lang_label = LANGUAGE_NAMES.get(detected_language, detected_language)
        print(f"Best transcription in {detected_lang_label}: '{best_transcription}'")

        # Format output message
        if detected_language == 'en':
            response_message = f"Transcription ({detected_lang_label}): {best_transcription}"
        else:
            response_message = f"Transcription ({detected_lang_label}): {best_transcription}"
            try:
                print(f"Translating '{best_transcription}' from {detected_language} to English...")
                english_translation = translate_text(
                    text=best_transcription,
                    source_lang=detected_language,
                    target_lang="en"
                )
                if english_translation:
                    response_message += f"\n\nEnglish translation: {english_translation}"
                    print(f"Translation result: {english_translation}")
                else:
                    print("Translation returned empty result")
            except Exception as translation_error:
                print(f"Could not translate text: {str(translation_error)}")
                response_message += f"\n\n(Translation unavailable: {str(translation_error)})"

        return response_message, None, 200

    except Exception as e:
        print(f"Error with Spitch transcription: {str(e)}")
        return None, f"Transcription error: {str(e)}", 500
