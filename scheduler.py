import time
import logging
import hashlib
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import config
from database import DatabaseManager
from espn_client import ESPNClient
from formatter import PostFormatter
from telegram_publisher import TelegramPublisher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("GamePulse.Scheduler")
ET_ZONE = ZoneInfo("America/New_York")

class GamePulseScheduler:

    def __init__(self, dry_run: bool = False):
        self.db = DatabaseManager(config.DB_PATH)
        self.espn = ESPNClient()
        self.publisher = TelegramPublisher()
        self.dry_run = dry_run

    def warmup_baseline(self):
        """
        On cold start/first run, seed existing ESPN items into DB silently
        so old past news/summaries are NOT published to Telegram.
        """
        logger.info("=== Cold Start Warmup: Seeding baseline DB so old items are skipped ===")
        today_et = datetime.now(ET_ZONE)
        today_et_str = today_et.strftime("%Y-%m-%d")

        # 1. Seed today's daily schedule
        schedule_key = f"daily_slate_{today_et_str}"
        self.db.mark_daily_schedule_processed(schedule_key)

        for league in config.ACTIVE_LEAGUES:
            sport = league["sport"]
            l_code = league["league"]

            # Seed existing games (previews, lineups, game starts, scoring plays) silently so past items are NOT published
            events = self.espn.get_scoreboard(sport, l_code)
            for ev in events:
                event_id = str(ev["id"])
                event_name = ev["name"]
                status_state = ev.get("status_state", "pre")
                status_detail = ev.get("status_detail", "")
                status_completed = ev.get("status_completed", False)

                # Silently mark lineups as processed so past lineups are not re-published
                self.db.mark_lineups_processed(event_id, sport, l_code, event_name)

                # If game is ALREADY in-progress ("in"/"live") or completed ("post"), SILENTLY mark game start & summary as processed
                if status_state in ["in", "live", "post"] or status_completed or "final" in status_detail.lower():
                    self.db.mark_game_start_processed(event_id, sport, l_code, event_name)
                    
                if status_completed or status_state == "post" or "final" in status_detail.lower():
                    self.db.mark_summary_processed(event_id, sport, l_code, event_name)

                # Silently seed existing quarter/halftime updates and plays so old past items before startup are NEVER published
                if status_detail:
                    detail_clean = re.sub(r'[^a-zA-Z0-9]', '', status_detail.lower())
                    quarter_key = f"{event_id}_quarter_{detail_clean}"
                    self.db.mark_quarter_update_processed(quarter_key, event_id)

                summary_data = self.espn.get_game_summary(sport, l_code, event_id)
                if summary_data:
                    plays = summary_data.get("plays", []) or summary_data.get("scoringPlays", [])
                    # For live games, do NOT seed plays from the current inning/period so live runs/goals are NEVER missed!
                    if status_state in ["in", "live"]:
                        curr_period_str = str(summary_data.get("period", "0"))
                        plays_to_seed = [p for p in plays if str(p.get("period", "0")) != curr_period_str]
                    else:
                        plays_to_seed = plays

                    for p in plays_to_seed:
                        p_id = str(p.get("id", p.get("sequenceNumber", "")))
                        p_text = str(p.get("text", "")).strip()
                        if p_text:
                            text_hash = hashlib.md5(p_text.lower().encode("utf-8")).hexdigest()[:12]
                            play_id_key = f"{event_id}_play_{p_id}" if p_id else f"{event_id}_text_{text_hash}"
                            play_text_key = f"{event_id}_text_{text_hash}"
                            self.db.mark_scoring_play_processed(play_id_key, event_id, p_text)
                            self.db.mark_scoring_play_processed(play_text_key, event_id, p_text)

            # Seed today's standings
            standing_key = f"{l_code}_{today_et_str}"
            self.db.mark_standing_processed(standing_key)

        logger.info("=== Baseline Seeding Complete: Bot is ready to publish NEW live events ONLY ===")

    def process_news(self):
        logger.info("=== Running Pillar 1: Flash Alerts, Injury Reports & Trade Alerts ===")
        for league in config.ACTIVE_LEAGUES:
            sport = league["sport"]
            l_code = league["league"]
            news_items = self.espn.get_news(sport, l_code, limit=25)
            
            for item in news_items:
                news_id = str(item["id"])
                headline = item.get("headline", "")
                if self.db.is_news_processed(news_id, headline):
                    continue

                msg_es, msg_en, image_url = PostFormatter.format_news(item, league)
                
                # Extract translated Spanish headline to check for Spanish duplicate stories
                headline_es = ""
                m_es = re.search(r'📌\s*<b>(.*?)</b>', msg_es)
                if m_es:
                    headline_es = m_es.group(1).strip()

                if headline_es and self.db.is_news_processed(news_id, headline_es):
                    logger.info(f"[{l_code.upper()}] Skipping duplicate Spanish story: {headline_es}")
                    continue

                # Mark BOTH English and Spanish headlines as processed IMMEDIATELY before sending to Telegram
                self.db.mark_news_processed(news_id, headline, sport, l_code)
                if headline_es:
                    self.db.mark_news_processed(news_id, headline_es, sport, l_code)

                logger.info(f"[{l_code.upper()}] New article/alert found: {headline}")

                if self.dry_run:
                    print(f"\n--- [DRY RUN - NEWS - ES] ---\n{msg_es}")
                    print(f"--- [DRY RUN - NEWS - EN] ---\n{msg_en}")
                else:
                    self.publisher.publish_bilingual(msg_es, msg_en, image_url)

    def process_daily_schedule(self):
        logger.info("=== Running Morning Daily Match Schedule Slate ===")
        today_et = datetime.now(ET_ZONE)
        today_et_str = today_et.strftime("%Y-%m-%d")
        schedule_key = f"daily_slate_{today_et_str}"

        if self.db.is_daily_schedule_processed(schedule_key):
            return

        self.db.mark_daily_schedule_processed(schedule_key)
        logger.info(f"Generating full daily match schedule slate for TODAY ({today_et_str})...")
        all_events_by_league = {}
        
        for league in config.ACTIVE_LEAGUES:
            sport = league["sport"]
            l_code = league["league"]
            events = self.espn.get_scoreboard(sport, l_code)
            
            today_events = []
            for ev in events:
                date_utc = ev.get("date", "")
                if date_utc:
                    try:
                        clean_str = date_utc.replace("Z", "+00:00")
                        dt_utc = datetime.fromisoformat(clean_str)
                        dt_et = dt_utc.astimezone(ET_ZONE)
                        if dt_et.strftime("%Y-%m-%d") == today_et_str:
                            today_events.append(ev)
                    except Exception as e:
                        logger.warning(f"Error parsing date {date_utc}: {e}")

            if today_events:
                all_events_by_league[l_code] = (league, today_events)

        if all_events_by_league:
            msg_es, msg_en = PostFormatter.format_daily_schedule(all_events_by_league)

            if self.dry_run:
                print(f"\n--- [DRY RUN - DAILY SCHEDULE - ES] ---\n{msg_es}")
                print(f"--- [DRY RUN - DAILY SCHEDULE - EN] ---\n{msg_en}")
            else:
                self.publisher.publish_bilingual(msg_es, msg_en)
            logger.info(f"Daily match schedule slate for TODAY ({today_et_str}) published successfully.")

    def process_stat_of_the_day(self):
        logger.info("=== Running Pillar 5: Stat of the Day & Curious Trends (EVERY VALID MATCHUP) ===")
        today_str = datetime.now(ET_ZONE).strftime("%Y-%m-%d")

        for league in config.ACTIVE_LEAGUES:
            sport = league["sport"]
            l_code = league["league"]
            events = self.espn.get_scoreboard(sport, l_code)

            for ev in events:
                event_id = str(ev["id"])
                event_name = ev["name"]
                status_state = ev.get("status_state", "pre")
                status_completed = ev.get("status_completed", False)

                if not status_completed and status_state == "pre":
                    date_utc = ev.get("date", "")
                    if date_utc:
                        try:
                            clean_str = date_utc.replace("Z", "+00:00")
                            dt_utc = datetime.fromisoformat(clean_str)
                            dt_et = dt_utc.astimezone(ET_ZONE)
                            ev_date_et = dt_et.strftime("%Y-%m-%d")
                            if ev_date_et != today_str:
                                continue  # Skip future games scheduled for upcoming months/weeks!
                        except Exception as e:
                            logger.warning(f"Error parsing date {date_utc}: {e}")

                    home_name = ev.get("home_team", {}).get("name", "")
                    away_name = ev.get("away_team", {}).get("name", "")
                    h_clean = re.sub(r'[^a-zA-Z0-9]', '', home_name.lower())
                    a_clean = re.sub(r'[^a-zA-Z0-9]', '', away_name.lower())
                    teams_sorted = "_".join(sorted([h_clean, a_clean]))
                    stat_key = f"stat_{l_code}_{teams_sorted}_{today_str}"

                    if not self.db.is_stat_of_day_processed(stat_key):
                        summary_data = self.espn.get_game_summary(sport, l_code, event_id)
                        self.db.mark_stat_of_day_processed(stat_key)
                        logger.info(f"[{l_code.upper()}] Publishing Stat of the Day: {event_name}")
                        msg_es, msg_en, image_url = PostFormatter.format_stat_of_day(ev, league, summary_data)

                        if self.dry_run:
                            print(f"\n--- [DRY RUN - STAT OF THE DAY - ES] ---\n{msg_es}")
                        else:
                            self.publisher.publish_bilingual(msg_es, msg_en, image_url)
                            time.sleep(1)

    def process_betting_picks(self):
        logger.info("=== Running Pillar 6: Sports Betting & Picks Engine ===")
        today_str = datetime.now(ET_ZONE).strftime("%Y-%m-%d")

        for league in config.ACTIVE_LEAGUES:
            sport = league["sport"]
            l_code = league["league"]
            events = self.espn.get_scoreboard(sport, l_code)

            for ev in events:
                event_id = str(ev["id"])
                event_name = ev["name"]
                status_state = ev.get("status_state", "pre")
                status_completed = ev.get("status_completed", False)

                if not status_completed and status_state == "pre":
                    # Require strictly that the game is scheduled for TODAY in ET timezone
                    date_utc = ev.get("date", "")
                    if date_utc:
                        try:
                            clean_str = date_utc.replace("Z", "+00:00")
                            dt_utc = datetime.fromisoformat(clean_str)
                            dt_et = dt_utc.astimezone(ET_ZONE)
                            ev_date_et = dt_et.strftime("%Y-%m-%d")
                            if ev_date_et != today_str:
                                continue  # Skip future games scheduled for upcoming months/weeks!
                        except Exception as e:
                            logger.warning(f"Error parsing date {date_utc}: {e}")

                    home_name = ev.get("home_team", {}).get("name", "")
                    away_name = ev.get("away_team", {}).get("name", "")
                    h_clean = re.sub(r'[^a-zA-Z0-9]', '', home_name.lower())
                    a_clean = re.sub(r'[^a-zA-Z0-9]', '', away_name.lower())
                    teams_sorted = "_".join(sorted([h_clean, a_clean]))
                    pick_key = f"pick_{l_code}_{teams_sorted}_{today_str}"

                    if not self.db.is_pick_processed(pick_key):
                        summary_data = self.espn.get_game_summary(sport, l_code, event_id)
                        self.db.mark_pick_processed(pick_key)
                        logger.info(f"[{l_code.upper()}] Publishing Pick of the Day for All Games: {event_name}")
                        msg_es, msg_en, image_url = PostFormatter.format_betting_pick(ev, league, summary_data)

                        if self.dry_run:
                            print(f"\n--- [DRY RUN - PICK OF THE DAY - ES] ---\n{msg_es}")
                        else:
                            self.publisher.publish_bilingual(msg_es, msg_en, image_url)
                            time.sleep(1)

    def process_scoreboard(self):
        logger.info("=== Running Ultra-Fast Live In-Game Tracker ===")
        for league in config.ACTIVE_LEAGUES:
            sport = league["sport"]
            l_code = league["league"]
            events = self.espn.get_scoreboard(sport, l_code)

            for ev in events:
                event_id = str(ev["id"])
                event_name = ev["name"]
                status_state = ev.get("status_state", "pre")
                status_detail = ev.get("status_detail", "")
                status_completed = ev.get("status_completed", False)
                summary_data = None  # EXPLICITLY RESET TO PREVENT VARIABLE LEAKAGE ACROSS GAMES!

                # STRICT TODAY DATE CHECK: Skip future off-season schedule games (e.g. August 29th NCAA games)
                date_utc = ev.get("date", "")
                if date_utc:
                    try:
                        clean_str = date_utc.replace("Z", "+00:00")
                        dt_utc = datetime.fromisoformat(clean_str)
                        dt_et = dt_utc.astimezone(ET_ZONE)
                        today_et = datetime.now(ET_ZONE)
                        ev_date_et = dt_et.strftime("%Y-%m-%d")
                        today_str = today_et.strftime("%Y-%m-%d")

                        diff_days = abs((dt_et.date() - today_et.date()).days)
                        if diff_days >= 1 and ev_date_et != today_str:
                            continue  # Skip non-today games scheduled for future months!
                    except Exception as e:
                        logger.warning(f"Error parsing date {date_utc}: {e}")

                # Pillar 2A: Pre-Game Preview & Betting Lines (Strictly ONCE per game, 2 to 3 hours before start with complete data)
                if not status_completed and status_state == "pre":
                    date_utc = ev.get("date", "")
                    hours_until_game = 999.0
                    if date_utc:
                        try:
                            clean_str = date_utc.replace("Z", "+00:00")
                            dt_utc = datetime.fromisoformat(clean_str)
                            dt_et = dt_utc.astimezone(ET_ZONE)
                            now_et = datetime.now(ET_ZONE)
                            hours_until_game = (dt_et - now_et).total_seconds() / 3600.0
                        except Exception as e:
                            logger.warning(f"Error parsing preview date {date_utc}: {e}")



                # Define event states
                is_truly_live = (status_state in ["in", "live"]) or (status_state != "pre" and status_state != "post")
                is_finished = status_completed or status_state == "post" or ("final" in status_detail.lower())

                # Feature: Official Confirmed Lineups Alert strictly 15 minutes before game start
                if status_state == "pre" and not self.db.is_lineup_processed(event_id):
                    date_utc = ev.get("date", "")
                    if date_utc:
                        try:
                            game_dt = datetime.fromisoformat(date_utc.replace("Z", "+00:00")).astimezone(ET_ZONE)
                            now_dt = datetime.now(ET_ZONE)
                            mins_until_game = (game_dt - now_dt).total_seconds() / 60.0

                            # Strictly 15 minutes or less prior to game start (0 to 15 mins)
                            if 0.0 <= mins_until_game <= 15.0:
                                summary_data = self.espn.get_game_summary(sport, l_code, event_id)
                                self.db.mark_lineup_processed(event_id, sport, l_code, event_name)
                                logger.info(f"[{l_code.upper()}] Official Confirmed Lineups Alert (15m prior to start): {event_name}")
                                msg_es, msg_en, image_url = PostFormatter.format_lineups_alert(ev, summary_data, league)

                                if self.dry_run:
                                    print(f"\n--- [DRY RUN - LINEUPS (15m BEFORE) - EN] ---\n{msg_en}")
                                else:
                                    self.publisher.publish_bilingual(msg_es, msg_en, image_url)
                        except Exception as e:
                            logger.warning(f"Error checking 15m lineup alert for {event_name}: {e}")

                # Check if Game is Finished (Post-Game Summary)
                if is_finished:
                    if not self.db.is_summary_processed(event_id):
                        self.db.mark_summary_processed(event_id, sport, l_code, event_name)
                        logger.info(f"[{l_code.upper()}] Finished Game Summary Triggered: {event_name}")
                        summary_data = self.espn.get_game_summary(sport, l_code, event_id)
                        if summary_data:
                            msg_es, msg_en, image_url = PostFormatter.format_summary(summary_data, ev, league)

                            if self.dry_run:
                                print(f"\n--- [DRY RUN - SUMMARY - ES] ---\n{msg_es}")
                            else:
                                self.publisher.publish_bilingual(msg_es, msg_en, image_url)

                # Pillar 2B: Continuous Minuto a Minuto Live Play Tracker (ONLY FOR LIVE GAMES)
                elif is_truly_live:
                    # 1. Game Started Alert (STRICTLY ONCE when game TRULY begins live on field)
                    if not self.db.is_game_start_processed(event_id):
                        self.db.mark_game_start_processed(event_id, sport, l_code, event_name)
                        logger.info(f"[{l_code.upper()}] Live Game Started Alert (TRULY LIVE): {event_name}")
                        msg_es, msg_en, image_url = PostFormatter.format_game_start(ev, league)

                        if self.dry_run:
                            print(f"\n--- [DRY RUN - GAME START - ES] ---\n{msg_es}")
                        else:
                            self.publisher.publish_bilingual(msg_es, msg_en, image_url)

                    # 2. Halftime / End of Period & Quarter Updates (ONLY FOR NBA, NFL, NHL - EXCLUDING MLB BASEBALL)
                    if l_code != "mlb" and sport != "baseball":
                        det_lower = status_detail.lower()
                        if any(term in det_lower for term in ["half", "descanso", "end of 1", "end of 2", "end of 3", "end 1", "end 2", "end 3"]):
                            detail_clean = re.sub(r'[^a-zA-Z0-9]', '', det_lower)
                            quarter_key = f"{event_id}_quarter_{detail_clean}"
                            if not self.db.is_quarter_update_processed(quarter_key):
                                self.db.mark_quarter_update_processed(quarter_key)
                                logger.info(f"[{l_code.upper()}] Halftime / Period Alert: {event_name} ({status_detail})")
                                summary_data = self.espn.get_game_summary(sport, l_code, event_id)
                                msg_es, msg_en, image_url = PostFormatter.format_quarter_update(ev, summary_data, league)

                                if self.dry_run:
                                    print(f"\n--- [DRY RUN - HALFTIME/PERIOD - ES] ---\n{msg_es}")
                                else:
                                    self.publisher.publish_bilingual(msg_es, msg_en, image_url)

                    # 3. Continuous Minuto a Minuto Live Play Alerts
                    summary_data = self.espn.get_game_summary(sport, l_code, event_id)
                    if summary_data:
                        plays = summary_data.get("plays", []) or summary_data.get("scoringPlays", [])
                        strict_keywords = ["scored", "scores", "homered", "home run", "grand slam", "touchdown", "field goal", "goal", "makes 3-pt", "three pointer", "dunked", "makes free throw", "sac fly", "pitching change", "substitution", "replaces", "red card", "ejected", "sent off", "interception", "fumble", "safety car", "red flag"]
                        scoring_plays = [
                            p for p in plays 
                            if p.get("scoring") or p.get("scoringPlay") or p.get("scoreValue", 0) > 0 
                            or any(kw in str(p.get("text", "")).lower() for kw in strict_keywords)
                        ]
                        
                        for p in scoring_plays:
                            p_id = str(p.get("id", p.get("sequenceNumber", hash(p.get("text", "")))))
                            p_text = str(p.get("text", "")).strip()
                            if not p_text:
                                continue
                                
                            text_hash = hashlib.md5(p_text.lower().encode("utf-8")).hexdigest()[:12]
                            play_id_key = f"{event_id}_play_{p_id}"
                            play_text_key = f"{event_id}_text_{text_hash}"
                            
                            if not self.db.is_scoring_play_processed(play_id_key) and not self.db.is_scoring_play_processed(play_text_key):
                                self.db.mark_scoring_play_processed(play_id_key, event_id, p_text)
                                self.db.mark_scoring_play_processed(play_text_key, event_id, p_text)
                                logger.info(f"[{l_code.upper()}] Minuto a Minuto Live Play Alert: {p_text}")
                                msg_es, msg_en, image_url = PostFormatter.format_mlb_run_alert(ev, p_text, league)
                                
                                if self.dry_run:
                                    print(f"\n--- [DRY RUN - MINUTO A MINUTO - ES] ---\n{msg_es}")
                                else:
                                    self.publisher.publish_bilingual(msg_es, msg_en, image_url)

    def process_standings(self):
        logger.info("=== Running Pillar 4: Community & Standings ===")
        today_key = datetime.now().strftime("%Y-%m-%d")
        
        for league in config.ACTIVE_LEAGUES:
            sport = league["sport"]
            l_code = league["league"]
            standing_key = f"{l_code}_{today_key}"

            if self.db.is_standing_processed(standing_key):
                continue

            try:
                logger.info(f"[{l_code.upper()}] Fetching daily standings...")
                conferences = self.espn.get_standings(sport, l_code)
                if conferences:
                    msg_es, msg_en = PostFormatter.format_standings(conferences, league)

                    if self.dry_run:
                        print(f"\n--- [DRY RUN - STANDINGS - ES] ---\n{msg_es}")
                    else:
                        self.publisher.publish_bilingual(msg_es, msg_en)

                    self.db.mark_standing_processed(standing_key)
            except Exception as e:
                logger.error(f"[{l_code.upper()}] Error processing standings: {e}")

    def run_once(self):
        logger.info("Starting single execution cycle...")
        self.warmup_baseline()
        self.process_news()
        self.process_scoreboard()
        self.process_standings()
        logger.info("Single execution cycle completed.")

    def start_loop(self):
        logger.info(f"Starting GamePulse continuous loop (News interval: {config.NEWS_CHECK_INTERVAL}s, Scoreboard interval: {config.SCOREBOARD_CHECK_INTERVAL}s)")
        
        # COLD START / FIRST RUN: Warmup DB baseline silently and flush old news cache so all recent news gets published
        try:
            self.db.flush_stale_news_cache()
            self.warmup_baseline()
        except Exception as e:
            logger.error(f"Error during baseline warmup: {e}")

        last_news_check = 0
        last_scoreboard_check = 0
        last_standings_check = 0
        last_schedule_check = 0

        while True:
            now = time.time()

            # 100% EXCLUSIVE: Minuto a Minuto Live Play-by-Play & Lineups with Odds
            if now - last_scoreboard_check >= config.SCOREBOARD_CHECK_INTERVAL:
                try:
                    self.process_scoreboard()
                except Exception as e:
                    logger.error(f"Error in process_scoreboard: {e}")
                last_scoreboard_check = now

            time.sleep(1)
