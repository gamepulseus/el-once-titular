import sqlite3
import logging
import re
from pathlib import Path
from typing import Union, Optional

logger = logging.getLogger("GamePulse.Database")

class DatabaseManager:
    """
    SQLite Manager for deduplication across news, previews, starts, scoring plays, quarter updates, and daily schedules.
    """

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = str(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Pillar 1: Processed News
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_news (
                    news_id TEXT PRIMARY KEY,
                    headline TEXT,
                    sport TEXT,
                    league TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Pillar 2A: Processed Previews
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_previews (
                    event_id TEXT PRIMARY KEY,
                    sport TEXT,
                    league TEXT,
                    event_name TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Pillar 2B: Processed Game Starts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_game_starts (
                    event_id TEXT PRIMARY KEY,
                    sport TEXT,
                    league TEXT,
                    event_name TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Pillar 2B Sub: Processed Live Scoring Plays (MLB Runs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_scoring_plays (
                    play_key TEXT PRIMARY KEY,
                    event_id TEXT,
                    play_text TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Safely check if play_text column exists, add if missing
            cursor.execute("PRAGMA table_info(processed_scoring_plays)")
            columns = [col[1] for col in cursor.fetchall()]
            if "play_text" not in columns:
                cursor.execute("ALTER TABLE processed_scoring_plays ADD COLUMN play_text TEXT")

            # Pillar 2B Sub: Processed Quarter/Period Updates (NBA/NFL/NHL)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_quarter_updates (
                    quarter_key TEXT PRIMARY KEY,
                    event_id TEXT,
                    period INTEGER,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Pillar 3: Processed Summaries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_summaries (
                    event_id TEXT PRIMARY KEY,
                    sport TEXT,
                    league TEXT,
                    event_name TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Pillar 4: Processed Standings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_standings (
                    standing_key TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Processed Daily Schedules / Carteleras
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_daily_schedules (
                    schedule_key TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Processed Lineups
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_lineups (
                    event_id TEXT PRIMARY KEY,
                    sport TEXT,
                    league TEXT,
                    event_name TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Processed Picks & Betting Insights
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_picks (
                    pick_key TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Processed Polls
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_polls (
                    poll_key TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            logger.info("SQLite database initialized successfully.")

            # In-memory sets for ultra-fast 0ms deduplication across ALL 4 Pillars
            self._sent_news_ids = set()
            self._sent_headlines = set()
            self._sent_lineups = set()
            self._sent_previews = set()
            self._sent_game_starts = set()
            self._sent_scoring_plays = set()
            self._sent_quarter_updates = set()
            self._sent_summaries = set()
            self._sent_standings = set()
            self._sent_daily_schedules = set()
            self._sent_polls = set()
            self._sent_stat_of_day = set()
            self._sent_picks = set()

            try:
                cursor.execute("SELECT news_id, headline FROM processed_news")
                for row in cursor.fetchall():
                    if row[0]: self._sent_news_ids.add(str(row[0]).strip())
                    if row[1]:
                        norm_h = re.sub(r'[^a-zA-Z0-9]', '', str(row[1]).lower())
                        if norm_h: self._sent_headlines.add(norm_h)

                cursor.execute("SELECT event_id FROM processed_lineups")
                for row in cursor.fetchall():
                    if row[0]: self._sent_lineups.add(str(row[0]).strip())

                cursor.execute("SELECT event_id FROM processed_previews")
                for row in cursor.fetchall():
                    if row[0]: self._sent_previews.add(str(row[0]).strip())

                cursor.execute("SELECT event_id FROM processed_game_starts")
                for row in cursor.fetchall():
                    if row[0]: self._sent_game_starts.add(str(row[0]).strip())

                cursor.execute("SELECT play_key FROM processed_scoring_plays")
                for row in cursor.fetchall():
                    if row[0]: self._sent_scoring_plays.add(str(row[0]).strip())

                cursor.execute("SELECT quarter_key FROM processed_quarter_updates")
                for row in cursor.fetchall():
                    if row[0]: self._sent_quarter_updates.add(str(row[0]).strip())

                cursor.execute("SELECT event_id FROM processed_summaries")
                for row in cursor.fetchall():
                    if row[0]: self._sent_summaries.add(str(row[0]).strip())

                cursor.execute("SELECT standing_key FROM processed_standings")
                for row in cursor.fetchall():
                    if row[0]: self._sent_standings.add(str(row[0]).strip())

                cursor.execute("SELECT schedule_key FROM processed_daily_schedules")
                for row in cursor.fetchall():
                    if row[0]: self._sent_daily_schedules.add(str(row[0]).strip())

                cursor.execute("SELECT poll_key FROM processed_polls")
                for row in cursor.fetchall():
                    if row[0]: self._sent_polls.add(str(row[0]).strip())

                cursor.execute("SELECT stat_key FROM processed_stat_of_day")
                for row in cursor.fetchall():
                    if row[0]: self._sent_stat_of_day.add(str(row[0]).strip())

                cursor.execute("SELECT pick_key FROM processed_picks")
                for row in cursor.fetchall():
                    if row[0]: self._sent_picks.add(str(row[0]).strip())

            except Exception as e:
                logger.warning(f"Error loading deduplication memory cache: {e}")

    # News Methods
    def flush_stale_news_cache(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM processed_news")
                conn.commit()
            if hasattr(self, "_sent_news_ids"): self._sent_news_ids.clear()
            if hasattr(self, "_sent_headlines"): self._sent_headlines.clear()
            logger.info("Cleared stale news cache from SQLite and memory.")
        except Exception as e:
            logger.warning(f"Error clearing stale news cache: {e}")

    def is_news_processed(self, news_id: str, headline: str = "") -> bool:
        clean_id = str(news_id).strip()
        norm_hl = re.sub(r'[^a-zA-Z0-9]', '', headline.lower()) if headline else ""

        if clean_id and clean_id in self._sent_news_ids:
            return True
        if norm_hl and norm_hl in self._sent_headlines:
            return True

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if norm_hl:
                cursor.execute("SELECT 1 FROM processed_news WHERE news_id = ?", (clean_id,))
                if cursor.fetchone():
                    self._sent_news_ids.add(clean_id)
                    return True
                cursor.execute("SELECT headline FROM processed_news")
                for row in cursor.fetchall():
                    if row[0]:
                        existing_norm = re.sub(r'[^a-zA-Z0-9]', '', str(row[0]).lower())
                        if existing_norm == norm_hl:
                            self._sent_headlines.add(norm_hl)
                            return True
            else:
                cursor.execute("SELECT 1 FROM processed_news WHERE news_id = ?", (clean_id,))
                if cursor.fetchone():
                    self._sent_news_ids.add(clean_id)
                    return True

        return False

    def mark_news_processed(self, news_id: str, headline: str, sport: str, league: str):
        clean_id = str(news_id).strip()
        norm_hl = re.sub(r'[^a-zA-Z0-9]', '', headline.lower()) if headline else ""

        if clean_id: self._sent_news_ids.add(clean_id)
        if norm_hl: self._sent_headlines.add(norm_hl)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_news (news_id, headline, sport, league)
                VALUES (?, ?, ?, ?)
            """, (clean_id, headline, sport, league))
            conn.commit()

    # Lineups Methods
    def is_lineup_processed(self, event_id: str) -> bool:
        return self.is_lineups_processed(event_id)

    def mark_lineup_processed(self, event_id: str, sport: str, league: str, event_name: str):
        return self.mark_lineups_processed(event_id, sport, league, event_name)

    def is_lineups_processed(self, event_id: str) -> bool:
        clean_id = str(event_id).strip()
        if clean_id in self._sent_lineups:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_lineups WHERE event_id = ?", (clean_id,))
            res = cursor.fetchone() is not None
            if res: self._sent_lineups.add(clean_id)
            return res

    def mark_lineups_processed(self, event_id: str, sport: str, league: str, event_name: str):
        clean_id = str(event_id).strip()
        self._sent_lineups.add(clean_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_lineups (event_id, sport, league, event_name)
                VALUES (?, ?, ?, ?)
            """, (clean_id, sport, league, event_name))
            conn.commit()

    # Previews Methods
    def is_preview_processed(self, event_id: str) -> bool:
        clean_id = str(event_id).strip()
        if clean_id in self._sent_previews:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_previews WHERE event_id = ?", (clean_id,))
            res = cursor.fetchone() is not None
            if res: self._sent_previews.add(clean_id)
            return res

    def mark_preview_processed(self, event_id: str, sport: str, league: str, event_name: str):
        clean_id = str(event_id).strip()
        self._sent_previews.add(clean_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_previews (event_id, sport, league, event_name)
                VALUES (?, ?, ?, ?)
            """, (clean_id, sport, league, event_name))
            conn.commit()

    # Game Starts Methods
    def is_game_start_processed(self, event_id: str) -> bool:
        clean_id = str(event_id).strip()
        if clean_id in self._sent_game_starts:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_game_starts WHERE event_id = ?", (clean_id,))
            res = cursor.fetchone() is not None
            if res: self._sent_game_starts.add(clean_id)
            return res

    def mark_game_start_processed(self, event_id: str, sport: str, league: str, event_name: str):
        clean_id = str(event_id).strip()
        self._sent_game_starts.add(clean_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_game_starts (event_id, sport, league, event_name)
                VALUES (?, ?, ?, ?)
            """, (clean_id, sport, league, event_name))
            conn.commit()

    # Live Scoring Plays Methods
    def is_scoring_play_processed(self, play_key: str) -> bool:
        clean_key = str(play_key).strip()
        if clean_key in self._sent_scoring_plays:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_scoring_plays WHERE play_key = ?", (clean_key,))
            res = cursor.fetchone() is not None
            if res: self._sent_scoring_plays.add(clean_key)
            return res

    def mark_scoring_play_processed(self, play_key: str, event_id: str, play_text: str):
        clean_key = str(play_key).strip()
        self._sent_scoring_plays.add(clean_key)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_scoring_plays (play_key, event_id, play_text)
                VALUES (?, ?, ?)
            """, (clean_key, str(event_id), play_text))
            conn.commit()

    # Quarter Update Methods
    def is_quarter_update_processed(self, quarter_key: str) -> bool:
        clean_key = str(quarter_key).strip()
        if clean_key in self._sent_quarter_updates:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_quarter_updates WHERE quarter_key = ?", (clean_key,))
            res = cursor.fetchone() is not None
            if res: self._sent_quarter_updates.add(clean_key)
            return res

    def mark_quarter_update_processed(self, quarter_key: str, event_id: str, period: int):
        clean_key = str(quarter_key).strip()
        self._sent_quarter_updates.add(clean_key)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_quarter_updates (quarter_key, event_id, period)
                VALUES (?, ?, ?)
            """, (clean_key, str(event_id), period))
            conn.commit()

    # Summaries Methods
    def is_summary_processed(self, event_id: str) -> bool:
        clean_id = str(event_id).strip()
        if clean_id in self._sent_summaries:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_summaries WHERE event_id = ?", (clean_id,))
            res = cursor.fetchone() is not None
            if res: self._sent_summaries.add(clean_id)
            return res

    def mark_summary_processed(self, event_id: str, sport: str, league: str, event_name: str):
        clean_id = str(event_id).strip()
        self._sent_summaries.add(clean_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_summaries (event_id, sport, league, event_name)
                VALUES (?, ?, ?, ?)
            """, (clean_id, sport, league, event_name))
            conn.commit()

    # Standings Methods
    def is_standing_processed(self, standing_key: str) -> bool:
        clean_key = str(standing_key).strip()
        if clean_key in self._sent_standings:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_standings WHERE standing_key = ?", (clean_key,))
            res = cursor.fetchone() is not None
            if res: self._sent_standings.add(clean_key)
            return res

    def mark_standing_processed(self, standing_key: str):
        clean_key = str(standing_key).strip()
        self._sent_standings.add(clean_key)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_standings (standing_key)
                VALUES (?)
            """, (clean_key,))
            conn.commit()

    # Daily Schedule Slate Methods
    def is_daily_schedule_processed(self, schedule_key: str) -> bool:
        clean_key = str(schedule_key).strip()
        if clean_key in self._sent_daily_schedules:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_daily_schedules WHERE schedule_key = ?", (clean_key,))
            res = cursor.fetchone() is not None
            if res: self._sent_daily_schedules.add(clean_key)
            return res

    def mark_daily_schedule_processed(self, schedule_key: str):
        clean_key = str(schedule_key).strip()
        self._sent_daily_schedules.add(clean_key)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_daily_schedules (schedule_key)
                VALUES (?)
            """, (clean_key,))
            conn.commit()

    # Pre-Game Poll Methods
    def is_poll_processed(self, poll_key: str) -> bool:
        clean_key = str(poll_key).strip()
        if clean_key in self._sent_polls:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_polls WHERE poll_key = ?", (clean_key,))
            res = cursor.fetchone() is not None
            if res: self._sent_polls.add(clean_key)
            return res

    def mark_poll_processed(self, poll_key: str):
        clean_key = str(poll_key).strip()
        self._sent_polls.add(clean_key)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_polls (poll_key)
                VALUES (?)
            """, (clean_key,))
            conn.commit()

    # Stat of the Day Methods
    def is_stat_of_day_processed(self, stat_key: str) -> bool:
        clean_key = str(stat_key).strip()
        if clean_key in self._sent_stat_of_day:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_stat_of_day WHERE stat_key = ?", (clean_key,))
            res = cursor.fetchone() is not None
            if res: self._sent_stat_of_day.add(clean_key)
            return res

    def mark_stat_of_day_processed(self, stat_key: str):
        clean_key = str(stat_key).strip()
        self._sent_stat_of_day.add(clean_key)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_stat_of_day (stat_key)
                VALUES (?)
            """, (clean_key,))
            conn.commit()

    # Picks & Betting Methods
    def is_pick_processed(self, pick_key: str) -> bool:
        clean_key = str(pick_key).strip()
        if clean_key in self._sent_picks:
            return True
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_picks WHERE pick_key = ?", (clean_key,))
            res = cursor.fetchone() is not None
            if res: self._sent_picks.add(clean_key)
            return res

    def mark_pick_processed(self, pick_key: str):
        clean_key = str(pick_key).strip()
        self._sent_picks.add(clean_key)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_picks (pick_key)
                VALUES (?)
            """, (clean_key,))
            conn.commit()
