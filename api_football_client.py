import logging
import json
import time
import urllib.request
import urllib.parse
from typing import Optional, List, Dict, Any
from config import API_FOOTBALL_KEY

logger = logging.getLogger("GamePulse.APIFootball")

class APIFootballClient:
    """Client for API-Football (api-sports.io / dashboard.api-football.com) v3 API."""

    BASE_URL = "https://v3.football.api-sports.io"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or API_FOOTBALL_KEY).strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "YOUR_API_FOOTBALL_KEY")

    def _fetch_json(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        if not self.is_configured():
            logger.warning("API-Football key not configured.")
            return None

        url = f"{self.BASE_URL}/{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        req = urllib.request.Request(url, headers={
            "x-apisports-key": self.api_key,
            "User-Agent": "GamePulse/2.0"
        })

        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        content = resp.read().decode('utf-8')
                        return json.loads(content)
            except Exception as e:
                if attempt < 2:
                    time.sleep(0.5)
                else:
                    logger.error(f"API-Football request error [{url}]: {e}")
                    return None
        return None

    def get_live_fixtures(self) -> List[Dict[str, Any]]:
        """Fetch all currently live soccer matches from API-Football."""
        res = self._fetch_json("fixtures", {"live": "all"})
        if not res or "response" not in res:
            return []
        return res.get("response", [])

    def get_fixtures_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Fetch all soccer matches for a specific date (YYYY-MM-DD)."""
        res = self._fetch_json("fixtures", {"date": date_str})
        if not res or "response" not in res:
            return []
        return res.get("response", [])

    def get_fixture_events(self, fixture_id: int) -> List[Dict[str, Any]]:
        """Fetch match events (Goals, Red Cards, Substitutions) for a fixture."""
        res = self._fetch_json("fixtures/events", {"fixture": fixture_id})
        if not res or "response" not in res:
            return []
        return res.get("response", [])

    def get_fixture_lineups(self, fixture_id: int) -> List[Dict[str, Any]]:
        """Fetch official confirmed starting lineups for a fixture."""
        res = self._fetch_json("fixtures/lineups", {"fixture": fixture_id})
        if not res or "response" not in res:
            return []
        return res.get("response", [])

    def get_injuries(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch injuries & sidelined players from API-Football."""
        params = {"date": date_str} if date_str else {"league": 39, "season": 2026}
        res = self._fetch_json("injuries", params)
        if not res or "response" not in res:
            return []
        return res.get("response", [])

    def get_transfers(self, player_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch latest transfers & signings from API-Football."""
        params = {"player": player_id} if player_id else {"team": 33}
        res = self._fetch_json("transfers", params)
        if not res or "response" not in res:
            return []
        return res.get("response", [])
