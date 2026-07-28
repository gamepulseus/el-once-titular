import unittest
import os
from pathlib import Path
from config import DB_PATH, ACTIVE_LEAGUES
from database import DatabaseManager
from espn_client import ESPNClient
from formatter import PostFormatter
from graphics import MatchupGraphics

class TestGamePulseSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager(DB_PATH)
        cls.espn = ESPNClient()

    def test_database_init(self):
        self.assertTrue(Path(DB_PATH).exists())

    def test_espn_news(self):
        news = self.espn.get_news("basketball", "nba", limit=1)
        self.assertTrue(isinstance(news, list))
        if news:
            n = news[0]
            league_info = ACTIVE_LEAGUES[0]
            msg_es, msg_en, img_url = PostFormatter.format_news(n, league_info)
            if msg_es and msg_en:
                self.assertIn("El Once Titular", msg_es)
                self.assertIn("ElOnceTitular", msg_en)

    def test_espn_scoreboard(self):
        events = self.espn.get_scoreboard("baseball", "mlb")
        self.assertTrue(isinstance(events, list))

    def test_graphic_generation(self):
        home_mock = {"name": "Tampa Bay Rays", "abbreviation": "TB", "logo": "http://a.espncdn.com/i/teamlogos/mlb/500/tb.png"}
        away_mock = {"name": "Cleveland Guardians", "abbreviation": "CLE", "logo": "http://a.espncdn.com/i/teamlogos/mlb/500/cle.png"}
        img_path = MatchupGraphics.generate_matchup_banner(home_mock, away_mock, "test_event")
        self.assertTrue(img_path is not None and os.path.exists(img_path))

if __name__ == "__main__":
    unittest.main()
