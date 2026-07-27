import time
import logging
import hashlib
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

    def process_news(self):
        logger.info("=== Running Pillar 1: Flash Alerts, Injury Reports & Trade Alerts ===")
        for league in config.ACTIVE_LEAGUES:
            sport = league["sport"]
            l_code = league["league"]
            news_items = self.espn.get_news(sport, l_code, limit=5)
            
            for item in news_items:
                news_id = item["id"]
                if self.db.is_news_processed(news_id):
                    continue

                headline = item["headline"]
                logger.info(f"[{l_code.upper()}] New article/alert found: {headline}")

                msg_es, msg_en, image_url = PostFormatter.format_news(item, league)

                if self.dry_run:
                    print(f"\n--- [DRY RUN - NEWS - ES] ---\n{msg_es}")
                    print(f"--- [DRY RUN - NEWS - EN] ---\n{msg_en}")
                else:
                    self.publisher.publish_bilingual(msg_es, msg_en, image_url)

                self.db.mark_news_processed(news_id, headline, sport, l_code)

    def process_daily_schedule(self):
        logger.info("=== Running Morning Daily Match Schedule Slate ===")
        today_et = datetime.now(ET_ZONE)
        today_et_str = today_et.strftime("%Y-%m-%d")
        schedule_key = f"daily_slate_{today_et_str}"

        if self.db.is_daily_schedule_processed(schedule_key):
            return

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

            self.db.mark_daily_schedule_processed(schedule_key)
            logger.info(f"Daily match schedule slate for TODAY ({today_et_str}) published successfully.")

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
                status_completed = ev.get("status_completed", False)

                # Pillar 2A: Pre-Game Preview & Betting Lines
                if not status_completed and status_state == "pre":
                    if not self.db.is_preview_processed(event_id):
                        summary_data = self.espn.get_game_summary(sport, l_code, event_id)
                        logger.info(f"[{l_code.upper()}] Pre-Game Analysis & Poll: {event_name}")
                        msg_es, msg_en, image_url = PostFormatter.format_preview(ev, league, summary_data)
                        q_es, q_en, opt_es, opt_en = PostFormatter.format_preview_poll(ev, league)

                        if self.dry_run:
                            print(f"\n--- [DRY RUN - PREVIEW - ES] ---\n{msg_es}")
                            print(f"--- [DRY RUN - POLL - ES] --- Question: {q_es}")
                        else:
                            self.publisher.publish_bilingual(msg_es, msg_en, image_url)
                            time.sleep(1)
                            self.publisher.publish_bilingual_poll(q_es, q_en, opt_es, opt_en)

                        self.db.mark_preview_processed(event_id, sport, l_code, event_name)

                # Pillar 2B: Game Started & Live In-Game Tracker (FAST LOOKUP ONLY FOR LIVE GAMES)
                elif not status_completed and status_state == "in":
                    # 1. Game Started Alert
                    if not self.db.is_game_start_processed(event_id):
                        logger.info(f"[{l_code.upper()}] Live Game Started Alert: {event_name}")
                        msg_es, msg_en, image_url = PostFormatter.format_game_start(ev, league)

                        if self.dry_run:
                            print(f"\n--- [DRY RUN - GAME START - ES] ---\n{msg_es}")
                        else:
                            self.publisher.publish_bilingual(msg_es, msg_en, image_url)

                        self.db.mark_game_start_processed(event_id, sport, l_code, event_name)

                    # Fetch Summary ONLY for LIVE games
                    summary_data = self.espn.get_game_summary(sport, l_code, event_id)

                    # 2. MLB Real-Time Run Alerts (Cada vez que un equipo haga carrera)
                    if "mlb" in l_code or "baseball" in sport:
                        plays = summary_data.get("plays", []) if summary_data else []
                        scoring_plays = [
                            p for p in plays 
                            if p.get("scoring") or p.get("scoringPlay") or p.get("scoreValue", 0) > 0 
                            or "scored" in str(p.get("text", "")).lower() 
                            or "homered" in str(p.get("text", "")).lower() 
                            or "grand slam" in str(p.get("text", "")).lower()
                        ]
                        
                        for p in scoring_plays:
                            p_id = str(p.get("id", p.get("sequenceNumber", hash(p.get("text", "")))))
                            p_text = str(p.get("text", "")).strip()
                            if not p_text or "nueva carrera" in p_text.lower():
                                continue
                                
                            text_hash = hashlib.md5(p_text.lower().encode("utf-8")).hexdigest()[:12]
                            play_id_key = f"{event_id}_run_{p_id}"
                            play_text_key = f"{event_id}_text_{text_hash}"
                            
                            if not self.db.is_scoring_play_processed(play_id_key) and not self.db.is_scoring_play_processed(play_text_key):
                                logger.info(f"[{l_code.upper()}] Live Run Alert Auto Publishing: {p_text}")
                                msg_es, msg_en, image_url = PostFormatter.format_mlb_run_alert(ev, p_text, league)
                                
                                if self.dry_run:
                                    print(f"\n--- [DRY RUN - MLB RUN ALERT - ES] ---\n{msg_es}")
                                else:
                                    self.publisher.publish_bilingual(msg_es, msg_en, image_url)

                                self.db.mark_scoring_play_processed(play_id_key, event_id, p_text)
                                self.db.mark_scoring_play_processed(play_text_key, event_id, p_text)

                    # 3. NBA / NFL / NHL Quarter Updates
                    else:
                        period = summary_data.get("header", {}).get("competitions", [{}])[0].get("status", {}).get("period", 0) if summary_data else 0
                        if period > 0:
                            quarter_key = f"{event_id}_q{period}"
                            if not self.db.is_quarter_update_processed(quarter_key):
                                logger.info(f"[{l_code.upper()}] Quarter/Period {period} Update: {event_name}")
                                msg_es, msg_en, image_url = PostFormatter.format_quarter_update(ev, summary_data, league)

                                if self.dry_run:
                                    print(f"\n--- [DRY RUN - QUARTER UPDATE - ES] ---\n{msg_es}")
                                else:
                                    self.publisher.publish_bilingual(msg_es, msg_en, image_url)

                                self.db.mark_quarter_update_processed(quarter_key, event_id, period)

                # Pillar 3: Post-Game Summaries for finished games
                elif status_completed or status_state == "post" or "final" in status_detail.lower():
                    if not self.db.is_summary_processed(event_id):
                        logger.info(f"[{l_code.upper()}] Finished Game found: {event_name}")
                        summary_data = self.espn.get_game_summary(sport, l_code, event_id)
                        if summary_data:
                            msg_es, msg_en, image_url = PostFormatter.format_summary(summary_data, ev, league)

                            if self.dry_run:
                                print(f"\n--- [DRY RUN - SUMMARY - ES] ---\n{msg_es}")
                            else:
                                self.publisher.publish_bilingual(msg_es, msg_en, image_url)

                            self.db.mark_summary_processed(event_id, sport, l_code, event_name)

    def process_standings(self):
        logger.info("=== Running Pillar 4: Community & Standings ===")
        today_key = datetime.now().strftime("%Y-%m-%d")
        
        for league in config.ACTIVE_LEAGUES:
            sport = league["sport"]
            l_code = league["league"]
            standing_key = f"{l_code}_{today_key}"

            if self.db.is_standing_processed(standing_key):
                continue

            logger.info(f"[{l_code.upper()}] Fetching daily standings...")
            conferences = self.espn.get_standings(sport, l_code)
            if conferences:
                msg_es, msg_en = PostFormatter.format_standings(conferences, league)

                if self.dry_run:
                    print(f"\n--- [DRY RUN - STANDINGS - ES] ---\n{msg_es}")
                else:
                    self.publisher.publish_bilingual(msg_es, msg_en)

                self.db.mark_standing_processed(standing_key)

    def run_once(self):
        logger.info("Starting single execution cycle...")
        self.process_daily_schedule()
        self.process_news()
        self.process_scoreboard()
        self.process_standings()
        logger.info("Single execution cycle completed.")

    def start_loop(self):
        logger.info(f"Starting GamePulse continuous loop (News interval: {config.NEWS_CHECK_INTERVAL}s, Scoreboard interval: {config.SCOREBOARD_CHECK_INTERVAL}s)")
        
        last_news_check = 0
        last_scoreboard_check = 0
        last_standings_check = 0
        last_schedule_check = 0

        while True:
            now = time.time()

            if now - last_schedule_check >= 3600:
                try:
                    self.process_daily_schedule()
                except Exception as e:
                    logger.error(f"Error in daily schedule loop: {e}")
                last_schedule_check = now

            if now - last_news_check >= config.NEWS_CHECK_INTERVAL:
                try:
                    self.process_news()
                except Exception as e:
                    logger.error(f"Error in news loop: {e}")
                last_news_check = now

            if now - last_scoreboard_check >= config.SCOREBOARD_CHECK_INTERVAL:
                try:
                    self.process_scoreboard()
                except Exception as e:
                    logger.error(f"Error in scoreboard loop: {e}")
                last_scoreboard_check = now

            if now - last_standings_check >= 43200:
                try:
                    self.process_standings()
                except Exception as e:
                    logger.error(f"Error in standings loop: {e}")
                last_standings_check = now

            time.sleep(2)
