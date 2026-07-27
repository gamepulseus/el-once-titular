import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ES = os.getenv("TELEGRAM_CHANNEL_ES", "")
TELEGRAM_CHANNEL_EN = os.getenv("TELEGRAM_CHANNEL_EN", "")

# Website Configuration (GamePulse Web Portal)
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "http://localhost:5000")

# LLM Translation Key (Optional - zero-cost template engine used if empty)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# SQLite DB Path
DB_PATH = BASE_DIR / "gamepulse.db"

# Active Sports & Leagues Configuration
ACTIVE_LEAGUES = [
    {
        "sport": "basketball",
        "league": "nba",
        "name_es": "NBA",
        "name_en": "NBA",
        "emoji": "🏀"
    },
    {
        "sport": "football",
        "league": "nfl",
        "name_es": "NFL",
        "name_en": "NFL",
        "emoji": "🏈"
    },
    {
        "sport": "baseball",
        "league": "mlb",
        "name_es": "MLB",
        "name_en": "MLB",
        "emoji": "⚾"
    },
    {
        "sport": "hockey",
        "league": "nhl",
        "name_es": "NHL",
        "name_en": "NHL",
        "emoji": "🏒"
    },
    {
        "sport": "football",
        "league": "college-football",
        "name_es": "NCAA Football",
        "name_en": "NCAA Football",
        "emoji": "🏈"
    },
    {
        "sport": "basketball",
        "league": "mens-college-basketball",
        "name_es": "NCAA Basketball",
        "name_en": "NCAA Basketball",
        "emoji": "🏀"
    }
]

# Ultra-Fast Live Intervals (Forced 10 Seconds for Instant Live Alerts)
NEWS_CHECK_INTERVAL = 60          # 1 minute
SCOREBOARD_CHECK_INTERVAL = 10    # 10 SECONDS (Instant Live Alerts)
PREVIEW_HOURS_AHEAD = 12          # Match previews within 12h
