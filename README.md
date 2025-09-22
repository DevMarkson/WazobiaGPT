# WhatsApp Voice Bot with Multi-Language TTS

A sophisticated WhatsApp bot that provides bidirectional voice and text processing with support for Nigerian languages (Yoruba, Igbo, Hausa) and English.

## 🎯 Features

### Voice-to-Text Transcription

- **Smart Language Detection**: Automatic language detection with manual override options
- **Language Prefix Commands**: Use `/yoruba`, `/igbo`, `/hausa`, or `/english` to improve transcription accuracy
- **Multi-Language Support**: Yoruba, Igbo, Hausa, and English
- **Quality Filtering**: Automatically filters out low-quality audio and noise

### Text-to-Speech Generation

- **Natural Voices**: High-quality native voices for each language
- **Simple Commands**: Send `/speak [Language] [Text]` to generate speech
- **WhatsApp Compatible**: Automatically converts audio to WhatsApp-supported formats

### Language Support

| Language    | Code | Voice          | Example Command                      |
| ----------- | ---- | -------------- | ------------------------------------ |
| **Yoruba**  | `yo` | Sade (Female)  | `/speak Yoruba Bawo ni o se wa?`     |
| **Igbo**    | `ig` | Ngozi (Female) | `/speak Igbo Ndewo, kedu ka i mere?` |
| **Hausa**   | `ha` | Amina (Female) | `/speak Hausa Sannu, yaya kake?`     |
| **English** | `en` | Lucy (Female)  | `/speak English Hello, how are you?` |

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- WhatsApp Business API access
- Spitch API key
- ngrok (for local development)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/DevMarkson/spitch-record.git
   cd spitch-record
   ```

2. **Create virtual environment**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:

   ```env
   WHATSAPP_API_TOKEN=your_whatsapp_api_token
   WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
   SPITCH_API_KEY=your_spitch_api_key
   WEBHOOK_VERIFY_TOKEN=your_webhook_verify_token
   ```

5. **Install FFmpeg** (for audio conversion)
   ```bash
   pip install imageio-ffmpeg
   ```

### Running the Bot

1. **Start the Flask application**

   ```bash
   python app.py
   ```

2. **Expose with ngrok** (for local development)

   ```bash
   ngrok http 5000
   ```

3. **Configure WhatsApp webhook**
   - Use the ngrok URL + `/webhook` as your webhook endpoint
   - Use your `WEBHOOK_VERIFY_TOKEN` for verification

## 📱 How to Use

### Voice Transcription

#### Method 1: Send Voice Message Directly

- Send any voice message to get automatic transcription
- The bot will detect the language and transcribe accordingly

#### Method 2: Set Language Preference

- Send `/yoruba` to set Yoruba as your preferred language
- Send `/igbo` to set Igbo as your preferred language
- Send `/hausa` to set Hausa as your preferred language
- Send `/english` to set English as your preferred language

#### Method 3: One-time Language Override

- Send `/yoruba` followed by your voice message
- Send `/igbo` followed by your voice message
- Send `/hausa` followed by your voice message
- Send `/english` followed by your voice message

### Text-to-Speech

Send a message in this format:

```
/speak [Language] [Text to convert to speech]
```

**Examples:**

```
/speak Yoruba Bawo ni o se wa?
/speak Igbo Ndewo, kedu ka i mere?
/speak Hausa Sannu, yaya kake?
/speak English Hello, how are you today?
```

The bot will:

1. Generate high-quality speech audio using native voices
2. Convert to WhatsApp-compatible format (MP3/OGG)
3. Send back as an audio message

## 🔧 Technical Details

### Architecture

- **Framework**: Flask (Python web framework)
- **Speech Recognition**: Spitch API
- **Speech Synthesis**: Spitch API with native voices
- **Audio Processing**: pydub with FFmpeg
- **WhatsApp Integration**: WhatsApp Business API v22.0

### Audio Processing Pipeline

1. **Voice Input**: Receives voice messages from WhatsApp
2. **Download**: Fetches audio files using WhatsApp Media API
3. **Transcription**: Processes audio through Spitch speech recognition
4. **TTS Generation**: Converts text to speech using Spitch synthesis
5. **Format Conversion**: Converts WAV to MP3/OGG for WhatsApp compatibility
6. **Delivery**: Uploads and sends audio back through WhatsApp

### Supported Audio Formats

- **Input**: OGG, AMR, MP3, MP4, WAV
- **Output**: MP3 (primary), OGG (fallback), WAV (emergency fallback)

## 📋 API Endpoints

### Webhook Endpoint

```
POST /webhook
```

Receives WhatsApp webhook events for message processing.

### Verification Endpoint

```
GET /webhook
```

Handles WhatsApp webhook verification during setup.

## 🛠️ Configuration

### Environment Variables

| Variable                   | Description                        | Required |
| -------------------------- | ---------------------------------- | -------- |
| `WHATSAPP_API_TOKEN`       | WhatsApp Business API access token | Yes      |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp phone number ID           | Yes      |
| `SPITCH_API_KEY`           | Spitch API key for speech services | Yes      |
| `WEBHOOK_VERIFY_TOKEN`     | Token for webhook verification     | Yes      |

### Voice Configuration

The bot uses carefully selected female voices for consistency:

```python
voice_mapping = {
    'yo': 'sade',      # Yoruba - Native female voice
    'ig': 'ngozi',     # Igbo - Native female voice
    'ha': 'amina',     # Hausa - Native female voice
    'en': 'lucy',      # English - Clear female voice
}
```

## 🔍 Troubleshooting

### Common Issues

**1. "FFmpeg not found" warnings**

```bash
pip install imageio-ffmpeg
```

**2. Audio format not supported by WhatsApp**

- The bot automatically falls back to supported formats
- Ensure FFmpeg is properly installed for optimal conversion

**3. Spitch API voice errors**

- Voice names must match exactly (case-sensitive)
- Refer to the voice mapping in the configuration section

**4. WhatsApp webhook not receiving messages**

- Verify ngrok is running and accessible
- Check webhook URL configuration in WhatsApp Business API
- Ensure `WEBHOOK_VERIFY_TOKEN` matches

### Debug Mode

Enable debug logging by modifying `app.py`:

```python
app.run(debug=True, host='0.0.0.0', port=5000)
```

## 📊 Performance

### Response Times

- **Voice Transcription**: 2-5 seconds (depending on audio length)
- **Text-to-Speech**: 3-8 seconds (including conversion and upload)
- **Language Detection**: <1 second

### Audio Quality

- **Input**: Supports various bitrates and formats
- **Output**: 128kbps MP3 for optimal quality/size balance
- **Voice Quality**: Native speaker quality with natural intonation

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Spitch API** for high-quality speech recognition and synthesis
- **WhatsApp Business API** for messaging platform integration
- **FFmpeg** for audio format conversion capabilities

## 📞 Support

For support, email [your-email@example.com] or create an issue in this repository.

---

**Made with ❤️ for the Nigerian tech community**

_Bringing voice technology to local languages and making communication more accessible._
