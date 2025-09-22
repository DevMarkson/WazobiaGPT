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
                            media_info_response = requests.get(
                                media_url, headers=headers)
                            if media_info_response.status_code != 200:
                                print(
                                    f"Failed to get media URL. Status: {media_info_response.status_code}")
                                print(f"Response: {media_info_response.text}")
                                return jsonify({"status": "error", "message": "Failed to get media URL"}), 500

                            media_info = media_info_response.json()
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

                                # Read the audio file and transcribe
                                with open(audio_file, "rb") as f:
                                    audio_content = f.read()
                                    print(
                                        f"Transcribing audio file: {audio_file}")

                                    # Use 'en' for English transcription (you can modify this based on your needs)
                                    response = client.speech.transcribe(
                                        language='en', content=audio_content)
                                    transcription = response.text
                                    print(f"Transcription: {transcription}")

                                if not transcription:
                                    print("No transcription result received")
                                    return jsonify({"status": "error", "message": "No transcription result"}), 500

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
