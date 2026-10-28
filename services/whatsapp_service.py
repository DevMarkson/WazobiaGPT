import os
import tempfile
import requests
from config import WHATSAPP_API_TOKEN, WHATSAPP_PHONE_NUMBER_ID

GRAPH_API_VERSION = "v22.0"
GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def _get_auth_headers():
    token = WHATSAPP_API_TOKEN or os.getenv('WHATSAPP_API_TOKEN')
    return {
        'Authorization': f'Bearer {token}'
    }


def send_whatsapp_text(recipient, text_body):
    """Send a plain text message to a WhatsApp user"""
    phone_number_id = WHATSAPP_PHONE_NUMBER_ID or os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    whatsapp_url = f"{GRAPH_API_BASE_URL}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "text": {
            "body": text_body
        }
    }
    headers = _get_auth_headers()
    headers['Content-Type'] = 'application/json'

    response = requests.post(whatsapp_url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Failed to send WhatsApp response. Status: {response.status_code}")
        print(f"Response: {response.text}")
    return response


def send_whatsapp_audio(recipient, media_id):
    """Send an audio message (by media ID) to a WhatsApp user"""
    phone_number_id = WHATSAPP_PHONE_NUMBER_ID or os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    whatsapp_url = f"{GRAPH_API_BASE_URL}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "audio",
        "audio": {
            "id": media_id
        }
    }
    headers = _get_auth_headers()
    headers['Content-Type'] = 'application/json'

    response = requests.post(whatsapp_url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Failed to send audio message. Status: {response.status_code}")
        print(f"Response: {response.text}")
    return response


def get_media_url(media_id):
    """Retrieve the download URL for a given WhatsApp media ID"""
    media_url = f"{GRAPH_API_BASE_URL}/{media_id}"
    headers = _get_auth_headers()

    print(f"Attempting to get media info from: {media_url}")
    token = headers.get('Authorization', '')
    print(f"Using headers: Authorization Bearer {token[:25]}...")

    response = requests.get(media_url, headers=headers)
    print(f"Media info response status: {response.status_code}")
    print(f"Media info response headers: {dict(response.headers)}")

    if response.status_code != 200:
        print(f"Failed to get media URL. Status: {response.status_code}")
        print(f"Response: {response.text}")
        return None, response

    media_info = response.json()
    print(f"Media info response: {media_info}")
    return media_info.get('url'), response


def download_media_file(download_url):
    """Download media file and save to a temporary file on disk"""
    headers = _get_auth_headers()
    response = requests.get(download_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to download audio. Status: {response.status_code}")
        return None, response

    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
        temp_file.write(response.content)
        audio_file_path = temp_file.name

    print(f"Audio file saved successfully: {audio_file_path}")
    return audio_file_path, response


def upload_audio_media(audio_filename, content_type):
    """Upload an audio file to WhatsApp and return the media ID"""
    phone_number_id = WHATSAPP_PHONE_NUMBER_ID or os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    upload_url = f"{GRAPH_API_BASE_URL}/{phone_number_id}/media"
    headers = _get_auth_headers()

    with open(audio_filename, 'rb') as audio_file:
        files = {
            'file': (audio_filename, audio_file, content_type),
        }
        data = {
            'type': 'audio',
            'messaging_product': 'whatsapp'
        }

        response = requests.post(upload_url, headers=headers, data=data, files=files)
        if response.status_code == 200:
            media_data = response.json()
            media_id = media_data.get('id')
            print(f"Audio uploaded successfully. Media ID: {media_id}")
            return media_id, response
        else:
            print(f"Failed to upload audio. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return None, response
