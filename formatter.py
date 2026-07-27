import json
import logging
from typing import Dict, Any, Tuple, Optional, List
import urllib.request
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
from config import OPENAI_API_KEY, GEMINI_API_KEY, SITE_BASE_URL
from graphics import MatchupGraphics

logger = logging.getLogger("GamePulse.Formatter")

ET_ZONE = ZoneInfo("America/New_York")

def format_datetime_et(iso_str: str, lang: str = "es") -> str:
    if not iso_str:
        return "N/A"
    try:
        clean_str = iso_str.replace("Z", "+00:00")
        dt_utc = datetime.fromisoformat(clean_str)
        dt_et = dt_utc.astimezone(ET_ZONE)
        
        if lang == "es":
            return dt_et.strftime("%d/%m/%Y - %I:%M %p ET")
        else:
            return dt_et.strftime("%m/%d/%Y - %I:%M %p ET")
    except Exception as e:
        logger.warning(f"Error parsing date {iso_str}: {e}")
        return iso_str

def free_google_translate(text: str, target_lang: str = "es") -> str:
    if not text:
        return text
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list) and len(data) > 0 and data[0]:
                sentences = data[0]
                translated = "".join([s[0] for s in sentences if isinstance(s, list) and len(s) > 0 and s[0]])
                return translated
    except Exception as e:
        logger.warning(f"Free translation error: {e}")
    return text

def translate_text(text: str, target_lang: str) -> str:
    if not text:
        return text

    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            prompt = f"Translate the following sports news text to {target_lang}. Keep player names accurate. Output ONLY translated text.\n\nText:\n{text}"
            payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.warning(f"Gemini translation failed: {e}")

    if OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            prompt = f"Translate the following sports text to {target_lang}. Return ONLY translated text.\n\nText:\n{text}"
            payload = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            })
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"OpenAI translation failed: {e}")

    lang_code = "es" if "span" in target_lang.lower() else "en"
    return free_google_translate(text, lang_code)

class PostFormatter:

    # Helper to format lines for both teams
    @staticmethod
    def _format_odds_block(odds: dict, home_team: dict, away_team: dict, lang: str = "es") -> str:
        ml_home = str(odds.get("moneyline_home", "N/A"))
        ml_away = str(odds.get("moneyline_away", "N/A"))
        details = odds.get("details", "N/A")
        over_under = str(odds.get("over_under", "N/A"))

        if ml_home.isdigit() or (ml_home.replace(".", "").isdigit() and not ml_home.startswith("-")):
            ml_home = f"+{ml_home}"
        if ml_away.isdigit() or (ml_away.replace(".", "").isdigit() and not ml_away.startswith("-")):
            ml_away = f"+{ml_away}"

        home_name = home_team.get("short_name", home_team.get("name", "Local"))
        away_name = away_team.get("short_name", away_team.get("name", "Visitante"))

        if ml_home.startswith("-"):
            home_tag_es, home_tag_en = "(Favorito)", "(Favorite)"
            away_tag_es, away_tag_en = "(Underdog)", "(Underdog)"
        elif ml_away.startswith("-"):
            away_tag_es, away_tag_en = "(Favorito)", "(Favorite)"
            home_tag_es, home_tag_en = "(Underdog)", "(Underdog)"
        else:
            home_tag_es = home_tag_en = away_tag_es = away_tag_en = ""

        if lang == "es":
            return (
                f"💰 <b>LÍNEAS DE APUESTAS & MONEYLINE (AMBOS EQUIPOS):</b>\n"
                f"• 🏠 <b>{home_name} {home_tag_es}:</b> <code>{ml_home}</code>\n"
                f"• 🚀 <b>{away_name} {away_tag_es}:</b> <code>{ml_away}</code>\n"
                f"🎯 <b>La Alta / Baja (Over/Under Total):</b> <code>{over_under}</code>\n"
                f"📊 <b>Línea / Spread:</b> <code>{details}</code>\n\n"
            )
        else:
            return (
                f"💰 <b>BETTING LINES & MONEYLINE (BOTH TEAMS):</b>\n"
                f"• 🏠 <b>{home_name} {home_tag_en}:</b> <code>{ml_home}</code>\n"
                f"• 🚀 <b>{away_name} {away_tag_en}:</b> <code>{ml_away}</code>\n"
                f"🎯 <b>Over / Under Total:</b> <code>{over_under}</code>\n"
                f"📊 <b>Line / Spread:</b> <code>{details}</code>\n\n"
            )

    @staticmethod
    def _format_lineups_block(summary_data: Optional[Dict[str, Any]], home_name: str, away_name: str, lang: str = "es") -> str:
        if not summary_data or "lineups" not in summary_data:
            if lang == "es":
                return "📋 <b>ALINEACIONES:</b> Confirmación en proceso por los equipos.\n\n"
            else:
                return "📋 <b>LINEUPS:</b> Official confirmation in progress.\n\n"

        lineups = summary_data.get("lineups", {})
        home_l = lineups.get("home", [])
        away_l = lineups.get("away", [])

        if not home_l and not away_l:
            if lang == "es":
                return "📋 <b>ALINEACIONES:</b> Por anunciar antes del inicio.\n\n"
            else:
                return "📋 <b>LINEUPS:</b> To be announced prior to kickoff/tip-off.\n\n"

        home_players = []
        for p in home_l[:9]:
            if isinstance(p, dict):
                home_players.append(p.get("name", ""))
            else:
                home_players.append(str(p))

        away_players = []
        for p in away_l[:9]:
            if isinstance(p, dict):
                away_players.append(p.get("name", ""))
            else:
                away_players.append(str(p))

        home_str = ", ".join(home_players) if home_players else "Por Anunciar / TBD"
        away_str = ", ".join(away_players) if away_players else "Por Anunciar / TBD"

        if lang == "es":
            return (
                f"📋 <b>ALINEACIONES CONFIRMADAS:</b>\n"
                f"• 🏠 <b>{home_name}:</b> {home_str}\n"
                f"• 🚀 <b>{away_name}:</b> {away_str}\n\n"
            )
        else:
            return (
                f"📋 <b>CONFIRMED LINEUPS:</b>\n"
                f"• 🏠 <b>{home_name}:</b> {home_str}\n"
                f"• 🚀 <b>{away_name}:</b> {away_str}\n\n"
            )

    # Feature 2 & 3: Smart News linking directly to GamePulse Web Portal 🌐
    @staticmethod
    def format_news(news_item: Dict[str, Any], league_info: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
        headline_en = news_item.get("headline", "")
        desc_en = news_item.get("description", "")
        published_utc = news_item.get("published", "")
        emoji = league_info.get("emoji", "⚡")
        sport = news_item.get("sport", "baseball")
        league = news_item.get("league", "mlb")
        league_name_es = league_info.get("name_es", league.upper())
        league_name_en = league_info.get("name_en", league.upper())
        
        raw_img = news_item["images"][0] if news_item.get("images") else None
        news_id = news_item.get("id", "news")
        image_url = MatchupGraphics.watermark_news_image(raw_img, news_id) if raw_img else None

        published_et_es = format_datetime_et(published_utc, "es") if published_utc else ""
        published_et_en = format_datetime_et(published_utc, "en") if published_utc else ""

        headline_es = translate_text(headline_en, "Spanish")
        desc_es = translate_text(desc_en, "Spanish")

        time_line_es = f"🕒 <i>{published_et_es}</i>\n\n" if published_et_es else ""
        time_line_en = f"🕒 <i>{published_et_en}</i>\n\n" if published_et_en else ""

        full_text_lower = (headline_en + " " + desc_en).lower()

        # Direct GamePulse Web Portal URL
        site_link = f"{SITE_BASE_URL}/noticia/{news_id}?sport={sport}&league={league}"

        # Check Injury Keywords 🚑
        injury_keywords = ['injur', 'il ', 'ir ', 'disabled list', 'out for', 'surgery', 'lesió', 'lesio', 'baja', 'descartad', 'hamstring', 'knee', 'shoulder', 'elbow']
        is_injury = any(k in full_text_lower for k in injury_keywords)

        # Check Trade/Transfer Keywords 🔄
        trade_keywords = ['trade', 'traded', 'transf', 'sign', 'waiv', 'acquir', 'deal', 'contract', 'traspaso', 'canje', 'fichaje', 'firmad']
        is_trade = any(k in full_text_lower for k in trade_keywords) and not is_injury

        if is_injury:
            header_es = f"🚑 <b>¡ALERTA DE LESIÓN Y BAJA!</b> | {league_name_es} ⚕️"
            header_en = f"🚑 <b>INJURY REPORT & OUT ALERT</b> | {league_name_en} ⚕️"
        elif is_trade:
            header_es = f"🔄 <b>¡ALERTA DE TRASPASO Y MOVIMIENTO!</b> | {league_name_es} 🤝"
            header_en = f"🔄 <b>TRADE & TRANSACTION ALERT</b> | {league_name_en} 🤝"
        else:
            header_es = f"🚨 <b>¡ALERTA DE ÚLTIMA HORA!</b> | {league_name_es} {emoji}"
            header_en = f"🚨 <b>BREAKING NEWS ALERT</b> | {league_name_en} {emoji}"

        msg_es = (
            f"{header_es}\n\n"
            f"📌 <b>{headline_es}</b>\n\n"
            f"{desc_es}\n\n"
            f"{time_line_es}"
            f"🔗 <a href='{site_link}'>Leer noticia completa en GamePulse</a>\n\n"
            f"📲 <i>Sigue a @GamePulseES para las mejores alertas en vivo.</i>"
        )

        msg_en = (
            f"{header_en}\n\n"
            f"📌 <b>{headline_en}</b>\n\n"
            f"{desc_en}\n\n"
            f"{time_line_en}"
            f"🔗 <a href='{site_link}'>Read full article on GamePulse</a>\n\n"
            f"📲 <i>Follow @GamePulseUS for instant live updates.</i>"
        )

        return msg_es, msg_en, image_url

    # Feature 1: Morning Daily Schedule / Cartelera del Día 📅
    @staticmethod
    def format_daily_schedule(all_events_by_league: Dict[str, Tuple[Dict[str, Any], List[Dict[str, Any]]]]) -> Tuple[str, str]:
        today_date = datetime.now(ET_ZONE).strftime("%d/%m/%Y")
        today_date_en = datetime.now(ET_ZONE).strftime("%m/%d/%Y")

        msg_es_parts = [f"📅 <b>CARTELERA COMPLETA DE PARTIDOS DEL DÍA</b> | {today_date} 🏆\n"]
        msg_en_parts = [f"📅 <b>FULL DAILY MATCH SCHEDULE & SLATE</b> | {today_date_en} 🏆\n"]

        for l_code, (league_info, events) in all_events_by_league.items():
            if not events:
                continue
            emoji = league_info.get("emoji", "🏆")
            l_name_es = league_info.get("name_es", l_code.upper())
            l_name_en = league_info.get("name_en", l_code.upper())

            msg_es_parts.append(f"{emoji} <b>{l_name_es} ({len(events)} Partidos):</b>")
            msg_en_parts.append(f"{emoji} <b>{l_name_en} ({len(events)} Games):</b>")

            for ev in events[:8]:
                home = ev.get("home_team", {})
                away = ev.get("away_team", {})
                date_utc = ev.get("date", "")
                time_et = format_datetime_et(date_utc, "es").split("-")[-1].strip() if date_utc else "TBD"
                
                h_name = home.get("short_name", home.get("name", "Home"))
                a_name = away.get("short_name", away.get("name", "Away"))

                h_pitcher = home.get("probable_pitcher")
                a_pitcher = away.get("probable_pitcher")

                if h_pitcher and h_pitcher != "Por Anunciar / TBD":
                    pitcher_info = f" (P: {h_pitcher} vs {a_pitcher})"
                else:
                    pitcher_info = ""

                msg_es_parts.append(f"• 🏠 <b>{h_name}</b> vs 🚀 <b>{a_name}</b> | ⏰ <code>{time_et}</code>{pitcher_info}")
                msg_en_parts.append(f"• 🏠 <b>{h_name}</b> vs 🚀 <b>{a_name}</b> | ⏰ <code>{time_et}</code>{pitcher_info}")

            msg_es_parts.append("")
            msg_en_parts.append("")

        msg_es_parts.append("📲 <i>Sigue cada partido minuto a minuto en @GamePulseES</i>")
        msg_en_parts.append("📲 <i>Follow every matchup live on @GamePulseUS</i>")

        return "\n".join(msg_es_parts), "\n".join(msg_en_parts)

    # Pillar 2: Previews
    @classmethod
    def format_preview(cls, event: Dict[str, Any], league_info: Dict[str, Any], summary_data: Optional[Dict[str, Any]] = None) -> Tuple[str, str, Optional[str]]:
        emoji = league_info.get("emoji", "🔮")
        league_code = event.get("league", "").lower()
        sport = event.get("sport", "baseball")
        league_name_es = league_info.get("name_es", league_code.upper())
        league_name_en = league_info.get("name_en", league_code.upper())
        
        home = event.get("home_team", {})
        away = event.get("away_team", {})
        odds = event.get("odds", {})
        
        date_utc = event.get("date", "")
        date_et_es = format_datetime_et(date_utc, "es")
        date_et_en = format_datetime_et(date_utc, "en")

        event_id = event.get("id", "preview")
        image_url = MatchupGraphics.generate_matchup_banner(home, away, event_id) or home.get("logo")
        match_site_url = f"{SITE_BASE_URL}/partido/{event_id}?sport={sport}&league={league_code}"

        lineups_block_es = cls._format_lineups_block(summary_data, home.get('short_name'), away.get('short_name'), "es")
        lineups_block_en = cls._format_lineups_block(summary_data, home.get('short_name'), away.get('short_name'), "en")

        odds_block_es = cls._format_odds_block(odds, home, away, "es")
        odds_block_en = cls._format_odds_block(odds, home, away, "en")

        if "mlb" in league_code or "baseball" in league_code:
            home_pitcher = home.get("probable_pitcher", "Por Anunciar / TBD")
            away_pitcher = away.get("probable_pitcher", "Por Anunciar / TBD")

            msg_es = (
                f"🔮 <b>ANÁLISIS PRE-PARTIDO MLB</b> ⚾\n\n"
                f"🆚 <b>{home.get('name')}</b> vs <b>{away.get('name')}</b>\n"
                f"📈 Récord Local: <code>{home.get('record', 'N/A')}</code> | Récord Visitante: <code>{away.get('record', 'N/A')}</code>\n\n"
                f"⏰ <b>Hora de Inicio (ET):</b> {date_et_es}\n\n"
                f"⚾ <b>PITCHERS PROBABLES INICIALES:</b>\n"
                f"• 🏠 <b>{home.get('short_name')}:</b> {home_pitcher}\n"
                f"• 🚀 <b>{away.get('short_name')}:</b> {away_pitcher}\n\n"
                f"{lineups_block_es}"
                f"{odds_block_es}"
                f"🔗 <a href='{match_site_url}'>Ver alineaciones y detalles en GamePulse</a>\n\n"
                f"📲 <i>Sigue a @GamePulseES para las mejores alertas en vivo.</i>"
            )

            msg_en = (
                f"🔮 <b>MLB GAME PREVIEW & ANALYSIS</b> ⚾\n\n"
                f"🆚 <b>{home.get('name')}</b> vs <b>{away.get('name')}</b>\n"
                f"📈 Home Record: <code>{home.get('record', 'N/A')}</code> | Away Record: <code>{away.get('record', 'N/A')}</code>\n\n"
                f"⏰ <b>Start Time (ET):</b> {date_et_en}\n\n"
                f"⚾ <b>PROBABLE STARTING PITCHERS:</b>\n"
                f"• 🏠 <b>{home.get('short_name')}:</b> {home_pitcher}\n"
                f"• 🚀 <b>{away.get('short_name')}:</b> {away_pitcher}\n\n"
                f"{lineups_block_en}"
                f"{odds_block_en}"
                f"🔗 <a href='{match_site_url}'>View lineups and details on GamePulse</a>\n\n"
                f"📲 <i>Follow @GamePulseUS for instant live updates.</i>"
            )

        else:
            msg_es = (
                f"🔮 <b>PREVIA DEL PARTIDO</b> | {league_name_es} {emoji}\n\n"
                f"🆚 <b>{home.get('name')}</b> vs <b>{away.get('name')}</b>\n"
                f"📈 Récord Local: <code>{home.get('record', 'N/A')}</code> | Visitante: <code>{away.get('record', 'N/A')}</code>\n\n"
                f"⏰ <b>Hora (ET):</b> {date_et_es}\n\n"
                f"{lineups_block_es}"
                f"{odds_block_es}"
                f"🔗 <a href='{match_site_url}'>Ver detalles del partido en GamePulse</a>\n\n"
                f"📲 <i>Sigue a @GamePulseES para las mejores alertas en vivo.</i>"
            )
            msg_en = (
                f"🔮 <b>GAME PREVIEW</b> | {league_name_en} {emoji}\n\n"
                f"🆚 <b>{home.get('name')}</b> vs <b>{away.get('name')}</b>\n"
                f"📈 Home Record: <code>{home.get('record', 'N/A')}</code> | Away: <code>{away.get('record', 'N/A')}</code>\n\n"
                f"⏰ <b>Time (ET):</b> {date_et_en}\n\n"
                f"{lineups_block_en}"
                f"{odds_block_en}"
                f"🔗 <a href='{match_site_url}'>View match details on GamePulse</a>\n\n"
                f"📲 <i>Follow @GamePulseUS for instant live updates.</i>"
            )

        return msg_es, msg_en, image_url

    # Interactive Poll Generator
    @staticmethod
    def format_preview_poll(event: Dict[str, Any], league_info: Dict[str, Any]) -> Tuple[str, str, List[str], List[str]]:
        emoji = league_info.get("emoji", "📊")
        home = event.get("home_team", {})
        away = event.get("away_team", {})
        
        home_name = home.get("name", "Equipo Local")
        away_name = away.get("name", "Equipo Visitante")

        question_es = f"📊 ¿Quién se llevará la victoria hoy? {emoji}"
        question_en = f"📊 Who wins today's matchup? {emoji}"

        options_es = [f"{home_name} 🏠", f"{away_name} 🚀"]
        options_en = [f"{home_name} 🏠", f"{away_name} 🚀"]

        return question_es, question_en, options_es, options_en

    # Pillar 2B: Game Start Alert
    @staticmethod
    def format_game_start(event: Dict[str, Any], league_info: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
        emoji = league_info.get("emoji", "🚀")
        league_code = event.get("league", "").lower()
        sport = event.get("sport", "baseball")
        league_name_es = league_info.get("name_es", league_code.upper())
        league_name_en = league_info.get("name_en", league_code.upper())

        home = event.get("home_team", {})
        away = event.get("away_team", {})
        detail = event.get("status_detail", "In Progress / En Vivo")

        event_id = event.get("id", "start")
        image_url = MatchupGraphics.generate_matchup_banner(home, away, event_id) or home.get("logo")
        match_site_url = f"{SITE_BASE_URL}/partido/{event_id}?sport={sport}&league={league_code}"

        if "mlb" in league_code or "baseball" in league_code:
            start_term_es = "¡PLAY BALL!"
            start_term_en = "PLAY BALL!"
        elif "nfl" in league_code or "football" in league_code:
            start_term_es = "¡KICKOFF!"
            start_term_en = "KICKOFF!"
        elif "nba" in league_code or "basketball" in league_code:
            start_term_es = "¡TIP-OFF!"
            start_term_en = "TIP-OFF!"
        else:
            start_term_es = "¡PARTIDO EN VIVO!"
            start_term_en = "GAME LIVE!"

        msg_es = (
            f"🚀 <b>{start_term_es}</b> | {league_name_es} {emoji}\n\n"
            f"⚡ <b>¡EL PARTIDO HA COMENZADO EN VIVO!</b>\n\n"
            f"🆚 <b>{home.get('name')}</b> vs <b>{away.get('name')}</b>\n"
            f"📍 <b>Estado:</b> <code>{detail}</code>\n\n"
            f"🔗 <a href='{match_site_url}'>Sigue el partido en vivo en GamePulse</a>\n\n"
            f"📲 <i>Sigue la acción minuto a minuto en @GamePulseES</i>"
        )

        msg_en = (
            f"🚀 <b>{start_term_en}</b> | {league_name_en} {emoji}\n\n"
            f"⚡ <b>GAME IS NOW LIVE!</b>\n\n"
            f"🆚 <b>{home.get('name')}</b> vs <b>{away.get('name')}</b>\n"
            f"📍 <b>Status:</b> <code>{detail}</code>\n\n"
            f"🔗 <a href='{match_site_url}'>Follow live game on GamePulse</a>\n\n"
            f"📲 <i>Follow live updates on @GamePulseUS</i>"
        )

        return msg_es, msg_en, image_url

    # MLB Run Scored Real-Time Alert
    @staticmethod
    def format_mlb_run_alert(event: Dict[str, Any], play_text: str, league_info: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
        home = event.get("home_team", {})
        away = event.get("away_team", {})
        detail = event.get("status_detail", "En Vivo")
        event_id = event.get("id", "run")
        sport = event.get("sport", "baseball")
        league = event.get("league", "mlb")

        play_text_es = translate_text(play_text, "Spanish")
        match_site_url = f"{SITE_BASE_URL}/partido/{event_id}?sport={sport}&league={league}"

        msg_es = (
            f"⚾ <b>¡CARRERA ANOTADA EN VIVO!</b> | MLB ⚾\n\n"
            f"🔥 <b>Jugada:</b> {play_text_es}\n\n"
            f"📊 <b>MARCADOR EN VIVO:</b>\n"
            f"🏠 <b>{home.get('name')}</b>: <b>{home.get('score', 0)}</b>\n"
            f"🚀 <b>{away.get('name')}</b>: <b>{away.get('score', 0)}</b>\n"
            f"📍 <b>Inning:</b> <code>{detail}</code>\n\n"
            f"🔗 <a href='{match_site_url}'>Sigue el marcador en vivo en GamePulse</a>\n\n"
            f"📲 <i>Sigue cada carrera al instante en @GamePulseES</i>"
        )

        msg_en = (
            f"⚾ <b>LIVE RUN SCORED!</b> | MLB ⚾\n\n"
            f"🔥 <b>Play:</b> {play_text}\n\n"
            f"📊 <b>LIVE SCORE:</b>\n"
            f"🏠 <b>{home.get('name')}</b>: <b>{home.get('score', 0)}</b>\n"
            f"🚀 <b>{away.get('name')}</b>: <b>{away.get('score', 0)}</b>\n"
            f"📍 <b>Status:</b> <code>{detail}</code>\n\n"
            f"🔗 <a href='{match_site_url}'>Follow live boxscore on GamePulse</a>\n\n"
            f"📲 <i>Follow every run live on @GamePulseUS</i>"
        )

        image_url = MatchupGraphics.generate_matchup_banner(home, away, event_id) or home.get("logo")
        return msg_es, msg_en, image_url

    # Quarter / Period Update
    @staticmethod
    def format_quarter_update(event: Dict[str, Any], summary_data: Optional[Dict[str, Any]], league_info: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
        emoji = league_info.get("emoji", "📊")
        league_code = event.get("league", "").lower()
        sport = event.get("sport", "basketball")
        league_name_es = league_info.get("name_es", "")
        league_name_en = league_info.get("name_en", "")

        home = event.get("home_team", {})
        away = event.get("away_team", {})
        detail = event.get("status_detail", "Reporte de Cuarto")
        event_id = event.get("id", "quarter")

        detail_es = translate_text(detail, "Spanish")
        match_site_url = f"{SITE_BASE_URL}/partido/{event_id}?sport={sport}&league={league_code}"

        leaders = summary_data.get("leaders", []) if summary_data else []
        leaders_str_es = ""
        leaders_str_en = ""
        if leaders:
            top_leaders = leaders[:4]
            for l in top_leaders:
                cat_translated = translate_text(l['category'], 'Spanish')
                leaders_str_es += f"• <b>{l['athlete']}</b> ({l['team']}): {cat_translated} - <code>{l['stats']}</code>\n"
                leaders_str_en += f"• <b>{l['athlete']}</b> ({l['team']}): {l['category']} - <code>{l['stats']}</code>\n"
        else:
            pitchers = summary_data.get("pitchers", {}) if summary_data else {}
            home_p = pitchers.get("home", "TBD")
            away_p = pitchers.get("away", "TBD")
            leaders_str_es = f"• 🏠 <b>{home.get('short_name')}:</b> {home_p}\n• 🚀 <b>{away.get('short_name')}:</b> {away_p}\n"
            leaders_str_en = f"• 🏠 <b>{home.get('short_name')}:</b> {home_p}\n• 🚀 <b>{away.get('short_name')}:</b> {away_p}\n"

        if "nhl" in league_code or "hockey" in league_code:
            type_es = "PERIODO"
            type_en = "PERIOD"
        else:
            type_es = "CUARTO / DESCANSO"
            type_en = "QUARTER / HALFTIME"

        msg_es = (
            f"📊 <b>REPORTE DE {type_es}</b> | {league_name_es} {emoji}\n\n"
            f"🏆 <b>MARCADOR ACTUAL:</b>\n"
            f"🏠 <b>{home.get('name')}</b>: <b>{home.get('score', 0)}</b>\n"
            f"🚀 <b>{away.get('name')}</b>: <b>{away.get('score', 0)}</b>\n"
            f"📍 <b>Estado:</b> <code>{detail_es}</code>\n\n"
            f"🌟 <b>JUGADORES DESTACADOS (AMBOS EQUIPOS):</b>\n"
            f"{leaders_str_es}\n"
            f"🔗 <a href='{match_site_url}'>Ver estadísticas en vivo en GamePulse</a>\n\n"
            f"📲 <i>Sigue la cobertura cuarto a cuarto en @GamePulseES</i>"
        )

        msg_en = (
            f"📊 <b>{type_en} RECAP & SCORES</b> | {league_name_en} {emoji}\n\n"
            f"🏆 <b>CURRENT SCORE:</b>\n"
            f"🏠 <b>{home.get('name')}</b>: <b>{home.get('score', 0)}</b>\n"
            f"🚀 <b>{away.get('name')}</b>: <b>{away.get('score', 0)}</b>\n"
            f"📍 <b>Status:</b> <code>{detail}</code>\n\n"
            f"🌟 <b>TOP PERFORMERS (BOTH TEAMS):</b>\n"
            f"{leaders_str_en}\n"
            f"🔗 <a href='{match_site_url}'>Follow live boxscore on GamePulse</a>\n\n"
            f"📲 <i>Follow quarter-by-quarter coverage on @GamePulseUS</i>"
        )

        image_url = MatchupGraphics.generate_matchup_banner(home, away, event_id) or home.get("logo")
        return msg_es, msg_en, image_url

    # Feature 4: Post-Game Results with GamePulse Match URL 🌐
    @staticmethod
    def format_summary(summary_data: Dict[str, Any], scoreboard_ev: Dict[str, Any], league_info: Dict[str, Any]) -> Tuple[str, str, Optional[str]]:
        emoji = league_info.get("emoji", "📊")
        league_code = scoreboard_ev.get("league", "").lower()
        sport = scoreboard_ev.get("sport", "baseball")
        league_name_es = league_info.get("name_es", "")
        league_name_en = league_info.get("name_en", "")

        home = scoreboard_ev.get("home_team", {})
        away = scoreboard_ev.get("away_team", {})

        home_score = int(home.get("score", 0))
        away_score = int(away.get("score", 0))

        if home_score > away_score:
            home_status = "🏆 WINNER"
            home_status_es = "🏆 GANADOR"
            away_status = ""
            away_status_es = ""
        elif away_score > home_score:
            away_status = "🏆 WINNER"
            away_status_es = "🏆 GANADOR"
            home_status = ""
            home_status_es = ""
        else:
            home_status = home_status_es = away_status = away_status_es = "🤝 EMPATE"

        # Pitching decisions (W, L, SV)
        decisions = summary_data.get("decisions", {}) if summary_data else {}
        win_p = decisions.get("win")
        loss_p = decisions.get("loss")
        save_p = decisions.get("save")

        decisions_block_es = ""
        decisions_block_en = ""
        if win_p or loss_p:
            decisions_block_es += "⚾ <b>DECISIONES DE PITCHEO:</b>\n"
            decisions_block_en += "⚾ <b>PITCHING DECISIONS:</b>\n"
            if win_p:
                decisions_block_es += f"• 🟢 <b>Ganó (W):</b> {win_p}\n"
                decisions_block_en += f"• 🟢 <b>Win (W):</b> {win_p}\n"
            if loss_p:
                decisions_block_es += f"• 🔴 <b>Perdió (L):</b> {loss_p}\n"
                decisions_block_en += f"• 🔴 <b>Loss (L):</b> {loss_p}\n"
            if save_p:
                decisions_block_es += f"• 🔒 <b>Salvó (SV):</b> {save_p}\n"
                decisions_block_en += f"• 🔒 <b>Save (SV):</b> {save_p}\n"
            decisions_block_es += "\n"
            decisions_block_en += "\n"

        # Leaders balanced from both teams
        leaders = summary_data.get("leaders", []) if summary_data else []
        leaders_str_es = ""
        leaders_str_en = ""
        if leaders:
            top_leaders = leaders[:4]
            for l in top_leaders:
                cat_translated = translate_text(l['category'], 'Spanish')
                leaders_str_es += f"• <b>{l['athlete']}</b> ({l['team']}): {cat_translated} - <code>{l['stats']}</code>\n"
                leaders_str_en += f"• <b>{l['athlete']}</b> ({l['team']}): {l['category']} - <code>{l['stats']}</code>\n"
        else:
            pitchers = summary_data.get("pitchers", {}) if summary_data else {}
            home_p = pitchers.get("home", "TBD")
            away_p = pitchers.get("away", "TBD")
            leaders_str_es = f"• 🏠 <b>{home.get('short_name')}:</b> {home_p}\n• 🚀 <b>{away.get('short_name')}:</b> {away_p}\n"
            leaders_str_en = f"• 🏠 <b>{home.get('short_name')}:</b> {home_p}\n• 🚀 <b>{away.get('short_name')}:</b> {away_p}\n"

        event_id = scoreboard_ev.get("id", "summary")
        match_site_url = f"{SITE_BASE_URL}/partido/{event_id}?sport={sport}&league={league_code}"

        msg_es = (
            f"📊 <b>RESULTADO FINAL POST-PARTIDO</b> | {league_name_es} {emoji}\n\n"
            f"🏠 <b>{home.get('name')}</b>: <b>{home_score}</b> {home_status_es}\n"
            f"🚀 <b>{away.get('name')}</b>: <b>{away_score}</b> {away_status_es}\n\n"
            f"{decisions_block_es}"
            f"🌟 <b>JUGADORES DESTACADOS (AMBOS EQUIPOS):</b>\n"
            f"{leaders_str_es}\n"
            f"🔗 <a href='{match_site_url}'>Ver resumen y detalles completos en GamePulse</a>\n\n"
            f"📲 <i>Sigue el análisis deportivo en vivo en @GamePulseES</i>"
        )

        msg_en = (
            f"📊 <b>POST-GAME FINAL SCORE & RECAP</b> | {league_name_en} {emoji}\n\n"
            f"🏠 <b>{home.get('name')}</b>: <b>{home_score}</b> {home_status}\n"
            f"🚀 <b>{away.get('name')}</b>: <b>{away_score}</b> {away_status}\n\n"
            f"{decisions_block_en}"
            f"🌟 <b>STAR PERFORMERS (BOTH TEAMS):</b>\n"
            f"{leaders_str_en}\n"
            f"🔗 <a href='{match_site_url}'>Watch full recap and details on GamePulse</a>\n\n"
            f"📲 <i>Follow live sports analysis on @GamePulseUS</i>"
        )

        image_url = MatchupGraphics.generate_matchup_banner(home, away, event_id) or home.get("logo")
        return msg_es, msg_en, image_url

    # Pillar 4: Standings
    @staticmethod
    def format_standings(conferences: list, league_info: Dict[str, Any]) -> Tuple[str, str]:
        emoji = league_info.get("emoji", "💬")
        league_name_es = league_info.get("name_es", "")
        league_name_en = league_info.get("name_en", "")

        msg_es_parts = [f"💬 <b>TABLA DE POSICIONES & CLASIFICACIÓN</b> | {league_name_es} {emoji}\n"]
        msg_en_parts = [f"💬 <b>LEAGUE STANDINGS & RANKINGS</b> | {league_name_en} {emoji}\n"]

        for conf in conferences[:2]:
            conf_name_en = conf.get("name", "Conference")
            conf_name_es = translate_text(conf_name_en, "Spanish")
            
            msg_es_parts.append(f"🏆 <b>{conf_name_es}</b>")
            msg_en_parts.append(f"🏆 <b>{conf_name_en}</b>")

            top_teams = conf.get("teams", [])[:5]
            for idx, t in enumerate(top_teams, 1):
                medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))
                msg_es_parts.append(f"{medal} <b>{t['team']}</b> | {t['wins']}-{t['losses']} | Racha: <code>{t['streak']}</code>")
                msg_en_parts.append(f"{medal} <b>{t['team']}</b> | {t['wins']}-{t['losses']} | Streak: <code>{t['streak']}</code>")
            
            msg_es_parts.append("")
            msg_en_parts.append("")

        msg_es_parts.append("📲 <i>Sigue las posiciones y estadísticas en @GamePulseES</i>")
        msg_en_parts.append("📲 <i>Follow standings & stats on @GamePulseUS</i>")

        return "\n".join(msg_es_parts), "\n".join(msg_en_parts)
