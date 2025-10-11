# WazobiaGPT - Your Nigerian WhatsApp Speech and Voice Bot with Multilingual Support

A WhatsApp bot that transcribes and translates voice messages between Nigerian languages (Yoruba, Igbo, Hausa) and English using the Spitch API, with integrated text-to-speech and speech-to-text capabilities for natural, multilingual communication.

## Features

- **Voice-to-Text**: Send voice messages for automatic transcription and translation
- **Text-to-Speech**: Convert text to speech with `/speak [Language] [Text]`
- **Language Support**: Yoruba, Igbo, Hausa, and English
- **Smart Detection**: Automatic language detection with manual override options

## 🚀 Try It Now!

**WhatsApp Number:** +1 (555) 163-7395

Simply send a WhatsApp message to the number above to start using the bot! No setup required on your end.

## Usage

### Voice Messages

- Send any voice message → Get transcription + English translation
- Set language preference: `/yoruba`, `/igbo`, `/hausa`, `/english`

### Text-to-Speech

```
/speak Yoruba Bawo ni o se wa?
/speak Igbo Ndewo, kedu ka i mere?
/speak Hausa Sannu, yaya kake?
/speak English Hello, how are you?
```

## Setup

### 1. Environment Variables

Create a `.env` file:

```env
WHATSAPP_API_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
SPITCH_API_KEY=your_spitch_key
WEBHOOK_VERIFY_TOKEN=your_verify_token
```

### 2. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python app.py

# Expose with ngrok (new terminal)
ngrok http 5000
```

### 3. Heroku Deployment

```bash
# Login and create app
heroku login
heroku create your-app-name

# Set environment variables
heroku config:set WHATSAPP_API_TOKEN=your_token
heroku config:set WHATSAPP_PHONE_NUMBER_ID=your_phone_id
heroku config:set SPITCH_API_KEY=your_spitch_key
heroku config:set WEBHOOK_VERIFY_TOKEN=your_verify_token

# Deploy
git push heroku main
```

### 4. WhatsApp Configuration

- Webhook URL: `https://your-app.herokuapp.com/webhook`
- Verify Token: Use your `WEBHOOK_VERIFY_TOKEN`

## Tech Stack

- **Backend**: Flask (Python)
- **Speech API**: Spitch v1.34.0
- **Deployment**: Heroku
- **Audio Processing**: pydub + FFmpeg

## Support This Project

If you find this WhatsApp translation bot useful, please give it a star on GitHub! ⭐

Your support helps others discover this project and motivates continued development.

[⭐ Star this repo](https://github.com/DevMarkson/WazobiaGPT) if you found it helpful!

---

**Made with ❤️ for the Nigerian tech community**
