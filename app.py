import os
from flask import Flask
import config
from routes.webhook import webhook_bp


def create_app():
    """Application factory for WazobiaGPT Flask application"""
    flask_app = Flask(__name__)
    flask_app.register_blueprint(webhook_bp)
    return flask_app


# Expose app instance for WSGI servers (Gunicorn, Railway, Heroku)
app = create_app()


if __name__ == '__main__':
    print("🤖 Spitch Translator Bot Starting...")
    print("=" * 50)
    print("Available Commands:")
    print("• /help - Show detailed help")
    print("• /commands - Show quick commands")
    print("• /yoruba, /igbo, /hausa, /english - Set language preference")
    print("• Send voice notes or text for translation")
    print("=" * 50)

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
