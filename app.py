from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import json
from spitch import Spitch

# Load environment variables
load_dotenv()

app = Flask(__name__)


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
                            # Get media ID and sender
                            media_id = message['audio']['id']
                            sender = message['from']
                            print(
                                f"Processing audio message {media_id} from {sender}")

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

                                # Try each language and find the best result
                                for lang_code in languages_to_try:
                                    try:
                                        print(
                                            f"Trying transcription with language: {language_names[lang_code]} ({lang_code})")
                                        response = client.speech.transcribe(
                                            language=lang_code, content=audio_content)
                                        transcription = response.text.strip()

                                        if transcription and len(transcription) > 0:
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

            return jsonify({"status": "no audio found"}), 200

        except Exception as e:
            print(f"Error processing webhook: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)
