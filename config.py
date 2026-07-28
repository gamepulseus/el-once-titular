import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8850309639:AAHLec9jo29DuEw7o8YB7O7rdTqt_zHQgvU")
TELEGRAM_CHANNEL_ES = os.getenv("TELEGRAM_CHANNEL_ES", "@GamePulseES")
TELEGRAM_CHANNEL_EN = os.getenv("TELEGRAM_CHANNEL_EN", "@GamePulseUS")

# AI Credentials
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Active Leagues Matrix
ACTIVE_LEAGUES = [
    {"sport": "baseball", "league": "mlb", "name": "MLB Béisbol", "name_en": "MLB Baseball", "icon": "⚾"},
    {"sport": "basketball", "league": "nba", "name": "NBA Baloncesto", "name_en": "NBA Basketball", "icon": "🏀"},
    {"sport": "football", "league": "nfl", "name": "NFL Fútbol Americano", "name_en": "NFL Football", "icon": "🏈"},
    {"sport": "hockey", "league": "nhl", "name": "NHL Hockey", "name_en": "NHL Hockey", "icon": "🏒"},
    {"sport": "football", "league": "college-football", "name": "NCAA Fútbol Colegial", "name_en": "NCAA College Football", "icon": "🎓"},
    {"sport": "basketball", "league": "mens-college-basketball", "name": "NCAA Baloncesto Colegial", "name_en": "NCAA College Basketball", "icon": "🎓"}
]

# Database Path
DB_PATH = os.getenv("DB_PATH", "gamepulse.db")

# Interval Speeds (Seconds)
NEWS_CHECK_INTERVAL = 60
SCOREBOARD_CHECK_INTERVAL = 1

# Base URL for Web Site
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://gamepulse.up.railway.app")
