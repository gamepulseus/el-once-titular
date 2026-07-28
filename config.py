import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Credentials (EL ONCE TITULAR)
TELEGRAM_BOT_TOKEN = "8822719172:AAE_adfmCnxpKBkAtXifH37SE529gHiye70"
TELEGRAM_CHANNEL_ES = "@ElOnceTitular"
TELEGRAM_CHANNEL_EN = ""

# AI & Base URLs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://gamepulse.us")

# Twitter / X API v2 Credentials
_tw_key = os.getenv("TWITTER_API_KEY", "").strip()
TWITTER_API_KEY = _tw_key if _tw_key else "ioZAqtWEhacjb0kuR7r5T9oqP"

_tw_sec = os.getenv("TWITTER_API_SECRET", "").strip()
TWITTER_API_SECRET = _tw_sec if _tw_sec else "4GxQEPFgc2H2dOaE9hDac1QTAgFh8eLF0mWckwkgTMgphZvrYe"

_tw_tok = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
TWITTER_ACCESS_TOKEN = _tw_tok if _tw_tok else "2081943886545539072-L0ABYruAV4mEgEfomOzyL3yIUCgGjK"

_tw_asec = os.getenv("TWITTER_ACCESS_SECRET", "").strip()
TWITTER_ACCESS_SECRET = _tw_asec if _tw_asec else "tpu6lB53BeQgRtneeiSYxMtcePB1iHbpjq5aHQRwVzj3y"

# API-Football (api-sports.io / dashboard.api-football.com) PRO Key (EL ONCE TITULAR)
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "").strip() or "cbb0f106154c72d158f3de7d4db9f27b"

# Active Leagues Matrix (STRICTLY REQUESTED SOCCER LEAGUES FOR 'EL ONCE TITULAR')
ACTIVE_LEAGUES = [
    # 1. Torneos Internacionales de Clubes
    {"sport": "soccer", "league": "uefa.champions", "name": "UEFA Champions League", "name_en": "UEFA Champions League", "icon": "⚽"},
    {"sport": "soccer", "league": "uefa.europa", "name": "UEFA Europa League", "name_en": "UEFA Europa League", "icon": "⚽"},
    {"sport": "soccer", "league": "uefa.europa.conf", "name": "UEFA Conference League", "name_en": "UEFA Conference League", "icon": "⚽"},
    {"sport": "soccer", "league": "conmebol.libertadores", "name": "Copa Libertadores", "name_en": "Copa Libertadores", "icon": "⚽"},
    {"sport": "soccer", "league": "conmebol.sudamericana", "name": "Copa Sudamericana", "name_en": "Copa Sudamericana", "icon": "⚽"},
    {"sport": "soccer", "league": "concacaf.champions", "name": "CONCACAF Champions Cup", "name_en": "CONCACAF Champions Cup", "icon": "⚽"},

    # 2. Top Ligas de Europa
    {"sport": "soccer", "league": "eng.1", "name": "Premier League Inglaterra", "name_en": "English Premier League", "icon": "⚽"},
    {"sport": "soccer", "league": "esp.1", "name": "LaLiga España", "name_en": "Spanish LaLiga", "icon": "⚽"},
    {"sport": "soccer", "league": "ita.1", "name": "Serie A Italia", "name_en": "Italian Serie A", "icon": "⚽"},
    {"sport": "soccer", "league": "ger.1", "name": "Bundesliga Alemania", "name_en": "German Bundesliga", "icon": "⚽"},
    {"sport": "soccer", "league": "fra.1", "name": "Ligue 1 Francia", "name_en": "French Ligue 1", "icon": "⚽"},
    {"sport": "soccer", "league": "ned.1", "name": "Eredivisie Países Bajos", "name_en": "Dutch Eredivisie", "icon": "⚽"},
    {"sport": "soccer", "league": "por.1", "name": "Primeira Liga Portugal", "name_en": "Portuguese Liga", "icon": "⚽"},

    # 3. Ligas Principales de Las Américas
    {"sport": "soccer", "league": "usa.1", "name": "MLS Fútbol EE.UU.", "name_en": "MLS Soccer", "icon": "⚽"},
    {"sport": "soccer", "league": "mex.1", "name": "Liga MX México", "name_en": "Liga MX Mexico", "icon": "⚽"},
    {"sport": "soccer", "league": "arg.1", "name": "Liga Argentina", "name_en": "Argentine Liga Profesional", "icon": "⚽"},
    {"sport": "soccer", "league": "bra.1", "name": "Brasileirão Brasil", "name_en": "Brazilian Serie A", "icon": "⚽"},
    {"sport": "soccer", "league": "col.1", "name": "Liga BetPlay Colombia", "name_en": "Colombian Liga BetPlay", "icon": "⚽"},
    {"sport": "soccer", "league": "ven.1", "name": "Liga FUTVE Venezuela", "name_en": "Venezuelan Liga FUTVE", "icon": "⚽"},

    # 4. Torneos de Selecciones Nacionales
    {"sport": "soccer", "league": "fifa.world", "name": "Copa Mundial FIFA", "name_en": "FIFA World Cup", "icon": "🏆"},
    {"sport": "soccer", "league": "uefa.euro", "name": "Eurocopa UEFA", "name_en": "UEFA Euro", "icon": "🏆"},
    {"sport": "soccer", "league": "conmebol.america", "name": "Copa América", "name_en": "Copa America", "icon": "🏆"},
    {"sport": "soccer", "league": "uefa.nations", "name": "UEFA Nations League", "name_en": "UEFA Nations League", "icon": "🏆"},
]

# Database Path
DB_PATH = os.getenv("DB_PATH", "gamepulse.db")

# Interval Speeds (Seconds)
NEWS_CHECK_INTERVAL = 60
SCOREBOARD_CHECK_INTERVAL = 1

# Base URL for Web Site
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://gamepulse.up.railway.app")
