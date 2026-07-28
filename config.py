import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Credentials
_bot_tok = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_BOT_TOKEN = _bot_tok if _bot_tok else "8850309639:AAHLec9jo29DuEw7o8YB7O7rdTqt_zHQgvU"

_chan_es = os.getenv("TELEGRAM_CHANNEL_ES", "").strip()
TELEGRAM_CHANNEL_ES = _chan_es if _chan_es else "@GamePulseES"

_chan_en = os.getenv("TELEGRAM_CHANNEL_EN", "").strip()
TELEGRAM_CHANNEL_EN = _chan_en if _chan_en else "@GamePulseUS"

# AI & Base URLs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://gamepulse.us")

# Twitter / X API v2 Credentials
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "ioZAqtWEhacjb0kuR7r5T9oqP")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "4GxQEPFgc2H2dOaE9hDac1QTAgFh8eLF0mWckwkgTMgphZvrYe")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "2081943886545539072-L0ABYruAV4mEgEfomOzyL3yIUCgGjK")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "tpu6lB53BeQgRtneeiSYxMtcePB1iHbpjq5aHQRwVzj3y")

# Active Leagues Matrix (ABSOLUTELY ALL ESPN GLOBAL SPORTS & LEAGUES)
ACTIVE_LEAGUES = [
    # Béisbol (Baseball)
    {"sport": "baseball", "league": "mlb", "name": "MLB Béisbol", "name_en": "MLB Baseball", "icon": "⚾"},
    {"sport": "baseball", "league": "college-baseball", "name": "NCAA Béisbol Colegial", "name_en": "NCAA College Baseball", "icon": "⚾"},
    {"sport": "baseball", "league": "wbsc", "name": "WBSC Béisbol Internacional", "name_en": "WBSC World Baseball", "icon": "⚾"},
    
    # Baloncesto (Basketball)
    {"sport": "basketball", "league": "nba", "name": "NBA Baloncesto", "name_en": "NBA Basketball", "icon": "🏀"},
    {"sport": "basketball", "league": "wnba", "name": "WNBA Baloncesto Femenino", "name_en": "WNBA Women's Basketball", "icon": "🏀"},
    {"sport": "basketball", "league": "mens-college-basketball", "name": "NCAA Baloncesto Masculino", "name_en": "NCAA Men's Basketball", "icon": "🎓"},
    {"sport": "basketball", "league": "womens-college-basketball", "name": "NCAA Baloncesto Femenino", "name_en": "NCAA Women's Basketball", "icon": "🎓"},
    {"sport": "basketball", "league": "euroleague", "name": "Euroliga Baloncesto", "name_en": "EuroLeague Basketball", "icon": "🏀"},
    
    # Fútbol Soccer (Ligas Internacionales Top Mundial)
    {"sport": "soccer", "league": "eng.1", "name": "Premier League Inglaterra", "name_en": "English Premier League", "icon": "⚽"},
    {"sport": "soccer", "league": "esp.1", "name": "LaLiga España", "name_en": "Spanish LaLiga", "icon": "⚽"},
    {"sport": "soccer", "league": "uefa.champions", "name": "UEFA Champions League", "name_en": "UEFA Champions League", "icon": "⚽"},
    {"sport": "soccer", "league": "ita.1", "name": "Serie A Italia", "name_en": "Italian Serie A", "icon": "⚽"},
    {"sport": "soccer", "league": "ger.1", "name": "Bundesliga Alemania", "name_en": "German Bundesliga", "icon": "⚽"},
    {"sport": "soccer", "league": "fra.1", "name": "Ligue 1 Francia", "name_en": "French Ligue 1", "icon": "⚽"},
    {"sport": "soccer", "league": "usa.1", "name": "MLS Fútbol EE.UU.", "name_en": "MLS Soccer", "icon": "⚽"},
    {"sport": "soccer", "league": "mex.1", "name": "Liga MX México", "name_en": "Liga MX Mexico", "icon": "⚽"},
    {"sport": "soccer", "league": "conmebol.libertadores", "name": "Copa Libertadores", "name_en": "Copa Libertadores", "icon": "⚽"},
    {"sport": "soccer", "league": "conmebol.sudamericana", "name": "Copa Sudamericana", "name_en": "Copa Sudamericana", "icon": "⚽"},
    {"sport": "soccer", "league": "uefa.europa", "name": "UEFA Europa League", "name_en": "UEFA Europa League", "icon": "⚽"},
    {"sport": "soccer", "league": "sau.1", "name": "Saudi Pro League", "name_en": "Saudi Pro League", "icon": "⚽"},
    {"sport": "soccer", "league": "arg.1", "name": "Liga Profesional Argentina", "name_en": "Argentine Primera División", "icon": "⚽"},
    {"sport": "soccer", "league": "bra.1", "name": "Brasileirão Série A", "name_en": "Brazilian Serie A", "icon": "⚽"},
    {"sport": "soccer", "league": "por.1", "name": "Primeira Liga Portugal", "name_en": "Portuguese Primeira Liga", "icon": "⚽"},
    {"sport": "soccer", "league": "ned.1", "name": "Eredivisie Países Bajos", "name_en": "Dutch Eredivisie", "icon": "⚽"},
    {"sport": "soccer", "league": "uefa.nations", "name": "UEFA Nations League", "name_en": "UEFA Nations League", "icon": "⚽"},
    {"sport": "soccer", "league": "fifa.world", "name": "Eliminatorias & Mundial FIFA", "name_en": "FIFA World Cup & Qualifiers", "icon": "⚽"},
    
    # Fútbol Americano (American Football)
    {"sport": "football", "league": "nfl", "name": "NFL Fútbol Americano", "name_en": "NFL Football", "icon": "🏈"},
    {"sport": "football", "league": "college-football", "name": "NCAA Fútbol Colegial", "name_en": "NCAA College Football", "icon": "🎓"},
    {"sport": "football", "league": "ufl", "name": "UFL Fútbol Americano", "name_en": "UFL Football", "icon": "🏈"},
    {"sport": "football", "league": "cfl", "name": "CFL Fútbol Canadiense", "name_en": "CFL Canadian Football", "icon": "🏈"},

    # Hockey sobre Hielo (Hockey)
    {"sport": "hockey", "league": "nhl", "name": "NHL Hockey", "name_en": "NHL Hockey", "icon": "🏒"},
    {"sport": "hockey", "league": "mens-college-hockey", "name": "NCAA Hockey Colegial", "name_en": "NCAA Men's Hockey", "icon": "🏒"},

    # Tenis (Tennis)
    {"sport": "tennis", "league": "atp", "name": "Tenis ATP Masculino", "name_en": "ATP Men's Tennis", "icon": "🎾"},
    {"sport": "tennis", "league": "wta", "name": "Tenis WTA Femenino", "name_en": "WTA Women's Tennis", "icon": "🎾"},

    # Automovilismo (Racing)
    {"sport": "racing", "league": "f1", "name": "Fórmula 1", "name_en": "Formula 1", "icon": "🏎️"},
    {"sport": "racing", "league": "nascar", "name": "NASCAR Cup Series", "name_en": "NASCAR Racing", "icon": "🏎️"},
    {"sport": "racing", "league": "indycar", "name": "IndyCar Series", "name_en": "IndyCar Series", "icon": "🏎️"},

    # Artes Marciales Mixtas (MMA) & Boxeo
    {"sport": "mma", "league": "ufc", "name": "UFC Artes Marciales Mixtas", "name_en": "UFC MMA", "icon": "🥊"},

    # Golf
    {"sport": "golf", "league": "pga", "name": "PGA Tour Golf", "name_en": "PGA Tour Golf", "icon": "⛳"},

    # Voleibol (Volleyball)
    {"sport": "volleyball", "league": "mens-college-volleyball", "name": "NCAA Voleibol Masculino", "name_en": "NCAA Men's Volleyball", "icon": "🏐"},
    {"sport": "volleyball", "league": "womens-college-volleyball", "name": "NCAA Voleibol Femenino", "name_en": "NCAA Women's Volleyball", "icon": "🏐"}
]

# Database Path
DB_PATH = os.getenv("DB_PATH", "gamepulse.db")

# Interval Speeds (Seconds)
NEWS_CHECK_INTERVAL = 60
SCOREBOARD_CHECK_INTERVAL = 1

# Base URL for Web Site
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://gamepulse.up.railway.app")
