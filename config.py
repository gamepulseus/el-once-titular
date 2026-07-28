import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Credentials
TELEGRAM_BOT_TOKEN = "8850309639:AAHLec9jo29DuEw7o8YB7O7rdTqt_zHQgvU"
TELEGRAM_CHANNEL_ES = "@GamePulseES"
TELEGRAM_CHANNEL_EN = "@GamePulseUS"

# AI & Base URLs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://gamepulse.us")

# Twitter / X API v2 Credentials
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "ioZAqtWEhacjb0kuR7r5T9oqP")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "4GxQEPFgc2H2dOaE9hDac1QTAgFh8eLF0mWckwkgTMgphZvrYe")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "2081943886545539072-L0ABYruAV4mEgEfomOzyL3yIUCgGjK")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "tpu6lB53BeQgRtneeiSYxMtcePB1iHbpjq5aHQRwVzj3y")

# Active Leagues Matrix (STRICTLY TIER-1 TOP MAJOR LEAGUES ONLY)
ACTIVE_LEAGUES = [
    # Béisbol (Baseball)
    {"sport": "baseball", "league": "mlb", "name": "MLB Béisbol", "name_en": "MLB Baseball", "icon": "⚾"},

    # Baloncesto (Basketball)
    {"sport": "basketball", "league": "nba", "name": "NBA Baloncesto", "name_en": "NBA Basketball", "icon": "🏀"},

    # Fútbol Soccer (Top Ligas Mundiales)
    {"sport": "soccer", "league": "uefa.champions", "name": "UEFA Champions League", "name_en": "UEFA Champions League", "icon": "⚽"},
    {"sport": "soccer", "league": "eng.1", "name": "Premier League Inglaterra", "name_en": "English Premier League", "icon": "⚽"},
    {"sport": "soccer", "league": "esp.1", "name": "LaLiga España", "name_en": "Spanish LaLiga", "icon": "⚽"},
    {"sport": "soccer", "league": "ita.1", "name": "Serie A Italia", "name_en": "Italian Serie A", "icon": "⚽"},
    {"sport": "soccer", "league": "usa.1", "name": "MLS Fútbol EE.UU.", "name_en": "MLS Soccer", "icon": "⚽"},
    {"sport": "soccer", "league": "conmebol.libertadores", "name": "Copa Libertadores", "name_en": "Copa Libertadores", "icon": "⚽"},
    {"sport": "soccer", "league": "mex.1", "name": "Liga MX México", "name_en": "Liga MX Mexico", "icon": "⚽"},

    # Fútbol Americano (American Football)
    {"sport": "football", "league": "nfl", "name": "NFL Fútbol Americano", "name_en": "NFL Football", "icon": "🏈"},

    # Hockey sobre Hielo (Hockey)
    {"sport": "hockey", "league": "nhl", "name": "NHL Hockey", "name_en": "NHL Hockey", "icon": "🏒"},

    # Automovilismo & Combate (Racing & MMA)
    {"sport": "racing", "league": "f1", "name": "Fórmula 1", "name_en": "Formula 1", "icon": "🏎️"},
    {"sport": "mma", "league": "ufc", "name": "UFC Artes Marciales Mixtas", "name_en": "UFC MMA", "icon": "🥊"},
]

# Database Path
DB_PATH = os.getenv("DB_PATH", "gamepulse.db")

# Interval Speeds (Seconds)
NEWS_CHECK_INTERVAL = 60
SCOREBOARD_CHECK_INTERVAL = 1

# Base URL for Web Site
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://gamepulse.up.railway.app")
