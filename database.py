import sqlite3
import logging
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

            # Processed Official Lineups
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_lineups (
                    event_id TEXT PRIMARY KEY,
                    sport TEXT,
                    league TEXT,
                    event_name TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            logger.info("SQLite database initialized successfully.")

    # News Methods
    def is_news_processed(self, news_id: str, headline: str = "") -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            clean_id = str(news_id).strip()
            clean_hl = headline.strip().lower()
            if clean_hl:
                cursor.execute(
                    "SELECT 1 FROM processed_news WHERE news_id = ? OR LOWER(TRIM(headline)) = ?",
                    (clean_id, clean_hl)
                )
            else:
                cursor.execute("SELECT 1 FROM processed_news WHERE news_id = ?", (clean_id,))
            return cursor.fetchone() is not None

    def mark_news_processed(self, news_id: str, headline: str, sport: str, league: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_news (news_id, headline, sport, league)
                VALUES (?, ?, ?, ?)
            """, (str(news_id), headline, sport, league))
            conn.commit()

    # Lineups Methods
    def is_lineups_processed(self, event_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_lineups WHERE event_id = ?", (str(event_id),))
            return cursor.fetchone() is not None

    def mark_lineups_processed(self, event_id: str, sport: str, league: str, event_name: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_lineups (event_id, sport, league, event_name)
                VALUES (?, ?, ?, ?)
            """, (str(event_id), sport, league, event_name))
            conn.commit()

    # Previews Methods
    def is_preview_processed(self, event_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_previews WHERE event_id = ?", (str(event_id),))
            return cursor.fetchone() is not None

    def mark_preview_processed(self, event_id: str, sport: str, league: str, event_name: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_previews (event_id, sport, league, event_name)
                VALUES (?, ?, ?, ?)
            """, (str(event_id), sport, league, event_name))
            conn.commit()

    # Game Starts Methods
    def is_game_start_processed(self, event_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_game_starts WHERE event_id = ?", (str(event_id),))
            return cursor.fetchone() is not None

    def mark_game_start_processed(self, event_id: str, sport: str, league: str, event_name: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_game_starts (event_id, sport, league, event_name)
                VALUES (?, ?, ?, ?)
            """, (str(event_id), sport, league, event_name))
            conn.commit()

    # Live Scoring Plays Methods
    def is_scoring_play_processed(self, play_key: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_scoring_plays WHERE play_key = ?", (str(play_key),))
            return cursor.fetchone() is not None

    def mark_scoring_play_processed(self, play_key: str, event_id: str, play_text: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_scoring_plays (play_key, event_id, play_text)
                VALUES (?, ?, ?)
            """, (str(play_key), str(event_id), play_text))
            conn.commit()

    # Quarter Update Methods
    def is_quarter_update_processed(self, quarter_key: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_quarter_updates WHERE quarter_key = ?", (str(quarter_key),))
            return cursor.fetchone() is not None

    def mark_quarter_update_processed(self, quarter_key: str, event_id: str, period: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_quarter_updates (quarter_key, event_id, period)
                VALUES (?, ?, ?)
            """, (str(quarter_key), str(event_id), period))
            conn.commit()

    # Summaries Methods
    def is_summary_processed(self, event_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_summaries WHERE event_id = ?", (str(event_id),))
            return cursor.fetchone() is not None

    def mark_summary_processed(self, event_id: str, sport: str, league: str, event_name: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_summaries (event_id, sport, league, event_name)
                VALUES (?, ?, ?, ?)
            """, (str(event_id), sport, league, event_name))
            conn.commit()

    # Standings Methods
    def is_standing_processed(self, standing_key: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_standings WHERE standing_key = ?", (str(standing_key),))
            return cursor.fetchone() is not None

    def mark_standing_processed(self, standing_key: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_standings (standing_key)
                VALUES (?)
            """, (str(standing_key),))
            conn.commit()

    # Daily Schedule Methods
    def is_daily_schedule_processed(self, schedule_key: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_daily_schedules WHERE schedule_key = ?", (str(schedule_key),))
            return cursor.fetchone() is not None

    def mark_daily_schedule_processed(self, schedule_key: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO processed_daily_schedules (schedule_key)
                VALUES (?)
            """, (str(schedule_key),))
            conn.commit()
