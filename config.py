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

# Active Leagues Matrix (ALL ESPN Global Sports & Leagues)
ACTIVE_LEAGUES = [
    # Béisbol (Baseball)
    {"sport": "baseball", "league": "mlb", "name": "MLB Béisbol", "name_en": "MLB Baseball", "icon": "⚾"},
    {"sport": "baseball", "league": "college-baseball", "name": "NCAA Béisbol Colegial", "name_en": "NCAA College Baseball", "icon": "⚾"},
    
    # Baloncesto (Basketball)
    {"sport": "basketball", "league": "nba", "name": "NBA Baloncesto", "name_en": "NBA Basketball", "icon": "🏀"},
    {"sport": "basketball", "league": "wnba", "name": "WNBA Baloncesto Femenino", "name_en": "WNBA Women's Basketball", "icon": "🏀"},
    {"sport": "basketball", "league": "mens-college-basketball", "name": "NCAA Baloncesto Colegial", "name_en": "NCAA College Basketball", "icon": "🎓"},
    
    # Fútbol (Soccer - Top Ligas Internacionales)
    {"sport": "soccer", "league": "eng.1", "name": "Premier League Inglaterra", "name_en": "English Premier League", "icon": "⚽"},
    {"sport": "soccer", "league": "esp.1", "name": "LaLiga España", "name_en": "Spanish LaLiga", "icon": "⚽"},
    {"sport": "soccer", "league": "uefa.champions", "name": "UEFA Champions League", "name_en": "UEFA Champions League", "icon": "⚽"},
    {"sport": "soccer", "league": "ita.1", "name": "Serie A Italia", "name_en": "Italian Serie A", "icon": "⚽"},
    {"sport": "soccer", "league": "ger.1", "name": "Bundesliga Alemania", "name_en": "German Bundesliga", "icon": "⚽"},
    {"sport": "soccer", "league": "fra.1", "name": "Ligue 1 Francia", "name_en": "French Ligue 1", "icon": "⚽"},
    {"sport": "soccer", "league": "usa.1", "name": "MLS Fútbol EE.UU.", "name_en": "MLS Soccer", "icon": "⚽"},
    {"sport": "soccer", "league": "mex.1", "name": "Liga MX México", "name_en": "Liga MX Mexico", "icon": "⚽"},
    {"sport": "soccer", "league": "conmebol.libertadores", "name": "Copa Libertadores", "name_en": "Copa Libertadores", "icon": "⚽"},
    {"sport": "soccer", "league": "uefa.europa", "name": "UEFA Europa League", "name_en": "UEFA Europa League", "icon": "⚽"},
    {"sport": "soccer", "league": "sau.1", "name": "Saudi Pro League", "name_en": "Saudi Pro League", "icon": "⚽"},
    
    # Fútbol Americano (American Football)
    {"sport": "football", "league": "nfl", "name": "NFL Fútbol Americano", "name_en": "NFL Football", "icon": "🏈"},
    {"sport": "football", "league": "college-football", "name": "NCAA Fútbol Colegial", "name_en": "NCAA College Football", "icon": "🎓"},

    # Hockey sobre Hielo (Hockey)
    {"sport": "hockey", "league": "nhl", "name": "NHL Hockey", "name_en": "NHL Hockey", "icon": "🏒"},

    # Tenis (Tennis)
    {"sport": "tennis", "league": "atp", "name": "Tenis ATP", "name_en": "ATP Tennis", "icon": "🎾"},
    {"sport": "tennis", "league": "wta", "name": "Tenis WTA", "name_en": "WTA Tennis", "icon": "🎾"},

    # Automovilismo (Racing)
    {"sport": "racing", "league": "f1", "name": "Fórmula 1", "name_en": "Formula 1", "icon": "🏎️"}
]

# Database Path
DB_PATH = os.getenv("DB_PATH", "gamepulse.db")

# Interval Speeds (Seconds)
NEWS_CHECK_INTERVAL = 60
SCOREBOARD_CHECK_INTERVAL = 1

# Base URL for Web Site
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://gamepulse.up.railway.app")
