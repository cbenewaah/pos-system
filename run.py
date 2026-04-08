"""
Application entry point for development.

Usage:
    python run.py

Or with Flask CLI (after pip install -r requirements.txt):
    flask --app run.py run
"""
import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app(os.environ.get("FLASK_CONFIG", "development"))

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=app.config.get("DEBUG", False),
    )
