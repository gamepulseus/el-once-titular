import json
import urllib.request
import urllib.parse
import re
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger("GamePulse.ESPN")
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

def clean_stat_value(cat_name: str, display_val: Any, val_raw: Any) -> str:
    cat_lower = str(cat_name).lower()
    text = str(display_val) if display_val else str(val_raw)
    val_str = str(val_raw) if val_raw is not None else ""

    # 1. Home Runs
    if 'home' in cat_lower or 'hr' in cat_lower or 'jonr' in cat_lower:
        match = re.search(r'(\d+)\s*HRs?\b', text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} HR"
        if val_str.isdigit() or (val_str.replace('.', '', 1).isdigit() and '.' in val_str):
            return f"{int(float(val_str))} HR"

    # 2. RBIs / Carreras Impulsadas
    if 'rbi' in cat_lower or 'carrera' in cat_lower or 'impulsad' in cat_lower:
        match = re.search(r'(\d+)\s*RBIs?\b', text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} RBI"
        if val_str.isdigit() or (val_str.replace('.', '', 1).isdigit() and '.' in val_str):
            return f"{int(float(val_str))} RBI"

    # 3. Strikeouts / Ponches
    if 'strikeout' in cat_lower or 'ponche' in cat_lower or cat_lower == 'k':
        match = re.search(r'(\d+)\s*K\b', text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} K"
        match_so = re.search(r'(\d+)\s*SO\b', text, re.IGNORECASE)
        if match_so:
            return f"{match_so.group(1)} K"
        if val_str.isdigit() or (val_str.replace('.', '', 1).isdigit() and '.' in val_str):
            return f"{int(float(val_str))} K"

    # 4. Stolen Bases / Bases Robadas
    if 'stolen' in cat_lower or 'robo' in cat_lower or 'sb' in cat_lower:
        match = re.search(r'(\d+)\s*SBs?\b', text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} SB"
        if val_str.isdigit() or (val_str.replace('.', '', 1).isdigit() and '.' in val_str):
            return f"{int(float(val_str))} SB"

    # 5. Hits
    if 'hit' in cat_lower or cat_lower == 'h':
        match = re.search(r'(\d+)\s*H\b', text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} Hits"
        if val_str.isdigit() or (val_str.replace('.', '', 1).isdigit() and '.' in val_str):
            return f"{int(float(val_str))} Hits"

    # 6. Batting Average
    if 'avg' in cat_lower or 'average' in cat_lower or 'promedio' in cat_lower:
        match_dec = re.search(r'(\.\d{3})', text)
        if match_dec:
            return match_dec.group(1)
        match_hits = re.search(r'^(\d+)-(\d+)', text)
        if match_hits:
            h, ab = int(match_hits.group(1)), int(match_hits.group(2))
            avg = h / ab if ab > 0 else 0
            return f"{avg:.3f}".lstrip('0')
        if '.' in val_str:
            try:
                v_num = float(val_str)
                return f"{v_num:.3f}".lstrip('0')
            except Exception:
                pass

    # 7. Wins
    if 'win' in cat_lower or 'victoria' in cat_lower or cat_lower == 'w':
        match = re.search(r'(\d+)\s*W\b', text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} W"
        if val_str.isdigit() or (val_str.replace('.', '', 1).isdigit() and '.' in val_str):
            return f"{int(float(val_str))} W"

    # 8. Saves
    if 'save' in cat_lower or 'salvado' in cat_lower or cat_lower == 'sv':
        match = re.search(r'(\d+)\s*SV\b', text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} SV"
        if val_str.isdigit() or (val_str.replace('.', '', 1).isdigit() and '.' in val_str):
            return f"{int(float(val_str))} SV"

    if val_str and (val_str.isdigit() or '.' in val_str):
        return val_str

    return text.split(',')[0] if ',' in text else text

class ESPNClient:
    """
    Client for ESPN public REST endpoints ($0 USD).
    """

    BASE_URL = "http://site.api.espn.com/apis/site/v2/sports"
    V2_STANDINGS_URL = "https://site.web.api.espn.com/apis/v2/sports"
    CORE_NEWS_URL = "http://now.core.api.espn.com/v1/sports/news"
    ATHLETE_URL = "http://site.api.espn.com/apis/common/v3/sports"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _fetch_json(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    content = resp.read().decode('utf-8')
                    return json.loads(content)
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    # Pillar 1: Flash Alerts ⚡ (.../news)
    def get_news(self, sport: str, league: str, limit: int = 15) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/{sport}/{league}/news?limit={limit}"
        data = self._fetch_json(url)
        if not data or "articles" not in data:
            return []

        articles = []
        for art in data.get("articles", []):
            art_id = str(art.get("id", art.get("headline", "")))
            headline = art.get("headline", "")
            description = art.get("description", art.get("story", ""))
            published = art.get("published", "")
            byline = art.get("byline", "")
            link = art.get("links", {}).get("web", {}).get("href", "")
            
            images = []
            for img in art.get("images", []):
                if isinstance(img, dict) and "url" in img:
                    images.append(img["url"])
            
            articles.append({
                "id": art_id,
                "headline": headline,
                "description": description,
                "published": published,
                "byline": byline if byline else "Redacción ESPN",
                "link": link,
                "images": images,
                "sport": sport,
                "league": league
            })
        return articles

    # Fetch 100% full-length article story paragraphs using ESPN Core API, Summary API & Scraping
    def get_full_article_content(self, article: Dict[str, Any]) -> List[str]:
        art_id = str(article.get("id", ""))
        link = article.get("link", "")
        sport = article.get("sport", "baseball")
        league = article.get("league", "mlb")
        story_html = ""

        # 1. Game Recap Link (recap?gameId=XXXX) -> Fetch from ESPN summary API
        game_match = re.search(r'gameId=(\d+)', link)
        if game_match:
            game_id = game_match.group(1)
            url = f"{self.BASE_URL}/{sport}/{league}/summary?event={game_id}"
            data = self._fetch_json(url)
            if data and "article" in data and "story" in data["article"]:
                story_html = data["article"]["story"]

        # 2. Core News API (for regular news stories)
        if not story_html and art_id and art_id.isdigit():
            url = f"{self.CORE_NEWS_URL}/{art_id}"
            data = self._fetch_json(url)
            if data and "headlines" in data and len(data["headlines"]) > 0:
                story_html = data["headlines"][0].get("story", "")

        # 3. Web Scraping Fallback
        if not story_html and link:
            try:
                req = urllib.request.Request(link, headers=self.headers)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    story_html = resp.read().decode("utf-8", errors="ignore")
            except Exception as e:
                logger.warning(f"Error scraping article link: {e}")

        if story_html:
            blocks = re.split(r'</p>|<br\s*/?>\s*<br\s*/?>|\n\n|\r\n\r\n', story_html)
            clean_paragraphs = []
            for b in blocks:
                text = re.sub(r'<[^>]+>', '', b).strip()
                if " -- " in text:
                    text = text.split(" -- ", 1)[-1].strip()
                elif " - " in text and len(text.split(" - ", 1)[0]) < 20:
                    text = text.split(" - ", 1)[-1].strip()

                if len(text) > 30 and not text.startswith("http") and not text.startswith("play") and "Terms of Use" not in text and "Privacy Policy" not in text and "Facebook Messenger" not in text:
                    clean_paragraphs.append(text)
            if clean_paragraphs:
                return clean_paragraphs

        desc = article.get("description", "")
        return [desc] if desc else ["Contenido completo de la noticia."]

    # Helper to parse pitcher from competitor object
    def _parse_pitcher(self, comp: dict) -> str:
        for p in comp.get("probables", []):
            if p.get("name") == "probableStartingPitcher" or p.get("abbreviation") == "SP" or "starter" in str(p.get("name")).lower():
                ath = p.get("athlete", {})
                if ath.get("displayName"):
                    return ath["displayName"]

        prob_starter = comp.get("probableStarter", {})
        if prob_starter and isinstance(prob_starter, dict):
            ath = prob_starter.get("athlete", {})
            if ath.get("displayName"):
                return ath["displayName"]

        return "Por Anunciar / TBD"

    # Helper to parse odds from competition or summary pickcenter
    def _parse_odds(self, competition: dict, summary_data: Optional[dict] = None) -> dict:
        odds_info = {
            "details": "N/A",
            "over_under": "N/A",
            "spread": "N/A",
            "moneyline_home": "N/A",
            "moneyline_away": "N/A"
        }

        if summary_data and "pickcenter" in summary_data and len(summary_data["pickcenter"]) > 0:
            pc = summary_data["pickcenter"][0]
            odds_info["details"] = pc.get("details", "N/A")
            odds_info["over_under"] = str(pc.get("overUnder", "N/A"))
            odds_info["spread"] = str(pc.get("spread", "N/A"))
            odds_info["moneyline_home"] = str(pc.get("homeTeamOdds", {}).get("moneyLine", "N/A"))
            odds_info["moneyline_away"] = str(pc.get("awayTeamOdds", {}).get("moneyLine", "N/A"))
            return odds_info

        if "odds" in competition and len(competition["odds"]) > 0:
            o = competition["odds"][0]
            odds_info["details"] = o.get("details", "N/A")
            odds_info["over_under"] = str(o.get("overUnder", "N/A"))
            odds_info["spread"] = str(o.get("spread", "N/A"))
            odds_info["moneyline_home"] = str(o.get("homeTeamOdds", {}).get("moneyLine", "N/A"))
            odds_info["moneyline_away"] = str(o.get("awayTeamOdds", {}).get("moneyLine", "N/A"))

        return odds_info

    # Helper to parse statistical leaders, both-teams performers, pitching decisions (W, L, SV), and COMPLETE BOXSCORE TABLES
    def _parse_leaders_and_decisions(self, data: dict) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
        parsed_leaders = []
        by_team = {}
        decisions = {"win": None, "loss": None, "save": None}
        boxscore_tables = {"home": [], "away": []}

        boxscore = data.get("boxscore", {})
        if "players" in boxscore:
            for idx, p_team in enumerate(boxscore["players"]):
                team_name = p_team.get("team", {}).get("displayName", "")
                team_abbrev = p_team.get("team", {}).get("abbreviation", team_name)
                side = "home" if idx == 0 else "away"
                
                by_team[team_abbrev] = []
                team_categories = []
                
                for cat in p_team.get("statistics", []):
                    cat_name = cat.get("name", "Estadísticas")
                    labels = cat.get("labels", [])
                    athletes_list = []

                    for ath in cat.get("athletes", []):
                        ath_name = ath.get("athlete", {}).get("displayName", "")
                        ath_id = ath.get("athlete", {}).get("id", "")
                        notes = ath.get("notes", [])
                        stats_vals = ath.get("stats", [])
                        
                        # Pitching decisions
                        for note in notes:
                            if isinstance(note, dict) and note.get("type") == "pitchingDecision":
                                dec_text = note.get("text", "")
                                if dec_text.startswith("W"):
                                    decisions["win"] = f"{ath_name} ({team_abbrev})"
                                elif dec_text.startswith("L"):
                                    decisions["loss"] = f"{ath_name} ({team_abbrev})"
                                elif dec_text.startswith("S") or dec_text.startswith("SV"):
                                    decisions["save"] = f"{ath_name} ({team_abbrev})"

                        if ath_name and stats_vals:
                            athletes_list.append({
                                "id": ath_id,
                                "name": ath_name,
                                "stats": stats_vals
                            })

                            # Pitching stats
                            if len(stats_vals) >= 6 and "." in str(stats_vals[0]):
                                ip, er, so = stats_vals[0], stats_vals[3], stats_vals[5]
                                by_team[team_abbrev].append({
                                    "id": ath_id,
                                    "team": team_abbrev,
                                    "category": "Pitcheo",
                                    "athlete": ath_name,
                                    "stats": f"{ip} IP, {so} K, {er} CL"
                                })
                            # Batting stats
                            elif len(stats_vals) >= 2:
                                h_ab = stats_vals[0]
                                if h_ab not in ["0-4", "0-3", "0-2", "0-1", "0-5"] and "-" in h_ab:
                                    by_team[team_abbrev].append({
                                        "id": ath_id,
                                        "team": team_abbrev,
                                        "category": "Bateo",
                                        "athlete": ath_name,
                                        "stats": f"{h_ab} H-AB"
                                    })

                    team_categories.append({
                        "name": cat_name,
                        "labels": labels,
                        "athletes": athletes_list
                    })

                boxscore_tables[side] = {
                    "team_name": team_name,
                    "categories": team_categories
                }

        # Balance performers from BOTH teams
        team_keys = list(by_team.keys())
        if len(team_keys) >= 2:
            team1, team2 = team_keys[0], team_keys[1]
            t1_list = by_team[team1][:2]
            t2_list = by_team[team2][:2]
            
            max_len = max(len(t1_list), len(t2_list))
            for i in range(max_len):
                if i < len(t1_list):
                    parsed_leaders.append(t1_list[i])
                if i < len(t2_list):
                    parsed_leaders.append(t2_list[i])

        if not parsed_leaders:
            leaders = data.get("leaders", [])
            if leaders:
                for leader_group in leaders:
                    team_name = leader_group.get("team", {}).get("displayName", "")
                    for l_cat in leader_group.get("leaders", []):
                        cat_name = l_cat.get("displayName", l_cat.get("name", ""))
                        for athlete in l_cat.get("leaders", []):
                            ath_name = athlete.get("athlete", {}).get("displayName", "")
                            ath_id = athlete.get("athlete", {}).get("id", "")
                            value_display = athlete.get("displayValue", "")
                            if ath_name:
                                parsed_leaders.append({
                                    "id": ath_id,
                                    "team": team_name,
                                    "category": cat_name,
                                    "athlete": ath_name,
                                    "stats": value_display
                                })

        return parsed_leaders[:4], decisions, boxscore_tables

    # Overall General League Leaders (Top 10 Overall in League for HR, RBI, AVG, Hits, Pitching, Points, etc.)
    def get_general_league_leaders(self, sport: str, league: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/{sport}/{league}/statistics"
        data = self._fetch_json(url)
        general_categories = []

        if data and "stats" in data:
            stats_obj = data["stats"]
            categories = stats_obj.get("categories", [])
            for cat in categories:
                cat_name = cat.get("displayName", cat.get("name", "Estadísticas"))
                leaders = []
                for item in cat.get("leaders", []):
                    ath = item.get("athlete", {})
                    ath_id = str(ath.get("id", ""))
                    ath_name = ath.get("displayName", "")
                    team_info = item.get("team", {})
                    team_abbrev = team_info.get("abbreviation", team_info.get("displayName", ""))
                    val_raw = item.get("value", "")
                    disp_val = item.get("displayValue", "")
                    
                    cleaned_val = clean_stat_value(cat_name, disp_val, val_raw)
                    
                    headshot_obj = ath.get("headshot", {})
                    if isinstance(headshot_obj, dict):
                        headshot = headshot_obj.get("href", f"https://a.espncdn.com/i/headshots/{league}/players/full/{ath_id}.png")
                    elif isinstance(headshot_obj, str) and headshot_obj.startswith("http"):
                        headshot = headshot_obj
                    else:
                        headshot = f"https://a.espncdn.com/i/headshots/{league}/players/full/{ath_id}.png"

                    if ath_name:
                        leaders.append({
                            "id": ath_id,
                            "name": ath_name,
                            "team_name": team_abbrev,
                            "headshot": headshot,
                            "display_value": cleaned_val
                        })
                if leaders:
                    general_categories.append({
                        "category": cat_name,
                        "leaders": leaders[:10]
                    })

        return general_categories

    # Pillar 2: Game Previews 🔮 (.../scoreboard?dates=YYYYMMDD)
    def get_scoreboard(self, sport: str, league: str, dates: Optional[str] = None) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/{sport}/{league}/scoreboard"
        if dates:
            url += f"?dates={dates}"
            
        data = self._fetch_json(url)
        if not data or "events" not in data:
            return []

        parsed_events = []
        for ev in data.get("events", []):
            event_id = str(ev.get("id"))
            name = ev.get("name", "")
            short_name = ev.get("shortName", "")
            date_str = ev.get("date", "")
            status_obj = ev.get("status", {}).get("type", {})
            status_state = status_obj.get("state", "pre")
            status_detail = status_obj.get("detail", "")
            status_completed = status_obj.get("completed", False)
            
            competitions = ev.get("competitions", [{}])[0]
            competitors = competitions.get("competitors", [])
            
            home_team = {}
            away_team = {}
            for comp in competitors:
                pitcher_name = self._parse_pitcher(comp)

                team_data = {
                    "id": comp.get("id"),
                    "name": comp.get("team", {}).get("displayName", ""),
                    "short_name": comp.get("team", {}).get("name", ""),
                    "abbreviation": comp.get("team", {}).get("abbreviation", ""),
                    "logo": comp.get("team", {}).get("logo", ""),
                    "score": comp.get("score", "0"),
                    "record": comp.get("records", [{}])[0].get("summary", "") if comp.get("records") else "",
                    "probable_pitcher": pitcher_name
                }
                if comp.get("homeAway") == "home":
                    home_team = team_data
                else:
                    away_team = team_data
                    
            odds_info = self._parse_odds(competitions)

            parsed_events.append({
                "id": event_id,
                "name": name,
                "short_name": short_name,
                "date": date_str,
                "status_state": status_state,
                "status_detail": status_detail,
                "status_completed": status_completed,
                "home_team": home_team,
                "away_team": away_team,
                "odds": odds_info,
                "sport": sport,
                "league": league
            })

        return parsed_events

    # Pillar 3: Quick Analysis & Full Boxscores 📊 (.../summary?event={game_id})
    def get_game_summary(self, sport: str, league: str, event_id: str) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_URL}/{sport}/{league}/summary?event={event_id}"
        data = self._fetch_json(url)
        if not data:
            return None

        header = data.get("header", {})
        boxscore = data.get("boxscore", {})
        game_info = data.get("gameInfo", {})
        plays = data.get("plays", [])

        header_comp = header.get("competitions", [{}])[0]

        # Extract event info directly from header for past, today & future games
        status_detail_raw = header_comp.get("status", {}).get("type", {}).get("detail", "Programado")
        date_iso = header_comp.get("date", "")
        status_formatted = format_datetime_et(date_iso, "es") if date_iso else status_detail_raw

        event_home = {}
        event_away = {}
        for comp in header_comp.get("competitors", []):
            t = comp.get("team", {})
            t_id = t.get("id", "")
            rec = comp.get("record", [{}])[0].get("summary", "") if comp.get("record") else ""
            t_data = {
                "id": t_id,
                "name": t.get("displayName", ""),
                "short_name": t.get("name", ""),
                "abbreviation": t.get("abbreviation", ""),
                "logo": t.get("logos", [{}])[0].get("href", "") if t.get("logos") else f"https://a.espncdn.com/i/teamlogos/{league}/500/{t.get('abbreviation', '').lower()}.png",
                "score": comp.get("score", "0"),
                "record": rec
            }
            if comp.get("homeAway") == "home":
                event_home = t_data
            else:
                event_away = t_data

        event_info = {
            "id": event_id,
            "name": f"{event_away.get('name', '')} at {event_home.get('name', '')}",
            "short_name": f"{event_away.get('short_name', '')} @ {event_home.get('short_name', '')}",
            "date": date_iso,
            "status_detail": status_formatted,
            "home_team": event_home,
            "away_team": event_away,
            "sport": sport,
            "league": league
        }

        header_pitchers = {"home": "Por Anunciar / TBD", "away": "Por Anunciar / TBD"}
        for comp in header_comp.get("competitors", []):
            side = comp.get("homeAway", "home")
            pitcher = self._parse_pitcher(comp)
            if pitcher != "Por Anunciar / TBD":
                header_pitchers[side] = pitcher

        lineups = {"home": [], "away": []}
        rosters = data.get("rosters", [])
        for r in rosters:
            home_away = r.get("homeAway", "home")
            for entry in r.get("roster", []):
                athlete_name = entry.get("athlete", {}).get("displayName", "")
                athlete_id = entry.get("athlete", {}).get("id", "")
                position = entry.get("position", {}).get("abbreviation", "")
                is_starter = entry.get("starter", False)
                if is_starter and athlete_name:
                    lineups[home_away].append({
                        "id": athlete_id,
                        "name": athlete_name,
                        "position": position
                    })

        parsed_leaders, decisions, boxscore_tables = self._parse_leaders_and_decisions(data)
        odds_info = self._parse_odds(header_comp, data)

        # Format play-by-play list preserving scoringPlay and scoring flags (FULL game timeline from start to finish)
        parsed_plays = []
        for p in plays:
            p_text = p.get("text", "").strip()
            p_period = p.get("period", {}).get("displayValue", "")
            p_clock = p.get("clock", {}).get("displayValue", "")
            is_scoring = p.get("scoringPlay", False) or p.get("scoreValue", 0) > 0
            if p_text:
                parsed_plays.append({
                    "id": p.get("id", ""),
                    "text": p_text,
                    "period": p_period,
                    "clock": p_clock,
                    "scoringPlay": is_scoring,
                    "scoring": is_scoring
                })

        return {
            "event_id": event_id,
            "event_info": event_info,
            "header": header,
            "boxscore": boxscore,
            "boxscore_tables": boxscore_tables,
            "leaders": parsed_leaders,
            "decisions": decisions,
            "lineups": lineups,
            "pitchers": header_pitchers,
            "odds": odds_info,
            "game_info": game_info,
            "plays": parsed_plays,
            "sport": sport,
            "league": league
        }

    # Teams list endpoint
    def get_teams(self, sport: str, league: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/{sport}/{league}/teams"
        data = self._fetch_json(url)
        if not data or "sports" not in data:
            return []

        teams = []
        try:
            teams_raw = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
            for item in teams_raw:
                t = item.get("team", {})
                t_id = t.get("id")
                name = t.get("displayName")
                abbrev = t.get("abbreviation")
                logo = t.get("logos", [{}])[0].get("href") if t.get("logos") else ""
                record = t.get("record", {}).get("items", [{}])[0].get("summary", "") if t.get("record") else ""
                color = t.get("color", "1C1C1E")
                
                teams.append({
                    "id": t_id,
                    "name": name,
                    "abbreviation": abbrev,
                    "logo": logo,
                    "record": record,
                    "color": color,
                    "sport": sport,
                    "league": league
                })
        except Exception as e:
            logger.error(f"Error parsing teams: {e}")

        return teams

    # Team detail & roster endpoint with safe position group parsing
    def get_team_detail(self, sport: str, league: str, team_id: str) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_URL}/{sport}/{league}/teams/{team_id}"
        data = self._fetch_json(url)
        if not data or "team" not in data:
            return None

        t = data.get("team", {})
        logo = t.get("logos", [{}])[0].get("href") if t.get("logos") else ""
        
        roster_url = f"{self.BASE_URL}/{sport}/{league}/teams/{team_id}/roster"
        roster_data = self._fetch_json(roster_url)
        athletes = []
        
        if roster_data and "athletes" in roster_data:
            for group in roster_data.get("athletes", []):
                if isinstance(group, dict) and "items" in group:
                    pos_group_name = group.get("position", "")
                    for ath in group.get("items", []):
                        ath_id = ath.get("id")
                        name = ath.get("fullName", ath.get("displayName", ""))
                        
                        headshot_obj = ath.get("headshot", {})
                        if isinstance(headshot_obj, dict):
                            headshot = headshot_obj.get("href", f"https://a.espncdn.com/i/headshots/{league}/players/full/{ath_id}.png")
                        elif isinstance(headshot_obj, str) and headshot_obj.startswith("http"):
                            headshot = headshot_obj
                        else:
                            headshot = f"https://a.espncdn.com/i/headshots/{league}/players/full/{ath_id}.png"
                        
                        pos_obj = ath.get("position", "")
                        if isinstance(pos_obj, dict):
                            position = pos_obj.get("abbreviation", pos_obj.get("displayName", pos_group_name))
                        else:
                            position = str(pos_group_name)
                            
                        jersey = ath.get("jersey", "")
                        athletes.append({
                            "id": ath_id,
                            "name": name,
                            "headshot": headshot,
                            "position": position,
                            "jersey": jersey
                        })
                elif isinstance(group, dict):
                    ath_id = group.get("id")
                    name = group.get("fullName", group.get("displayName", ""))
                    headshot_obj = group.get("headshot", {})
                    if isinstance(headshot_obj, dict):
                        headshot = headshot_obj.get("href", f"https://a.espncdn.com/i/headshots/{league}/players/full/{ath_id}.png")
                    elif isinstance(headshot_obj, str) and headshot_obj.startswith("http"):
                        headshot = headshot_obj
                    else:
                        headshot = f"https://a.espncdn.com/i/headshots/{league}/players/full/{ath_id}.png"
                        
                    pos_obj = group.get("position", "")
                    position = pos_obj.get("abbreviation", "") if isinstance(pos_obj, dict) else str(pos_obj)
                    jersey = group.get("jersey", "")
                    athletes.append({
                        "id": ath_id,
                        "name": name,
                        "headshot": headshot,
                        "position": position,
                        "jersey": jersey
                    })

        return {
            "id": t.get("id"),
            "name": t.get("displayName"),
            "abbreviation": t.get("abbreviation"),
            "logo": logo,
            "color": t.get("color", "1C1C1E"),
            "record": t.get("record", {}).get("items", [{}])[0].get("summary", "") if t.get("record") else "",
            "standing_summary": t.get("standingSummary", ""),
            "roster": athletes,
            "sport": sport,
            "league": league
        }

    # Athlete detail endpoint
    def get_athlete_detail(self, sport: str, league: str, athlete_id: str) -> Optional[Dict[str, Any]]:
        url = f"{self.ATHLETE_URL}/{sport}/{league}/athletes/{athlete_id}"
        data = self._fetch_json(url)
        if not data or "athlete" not in data:
            return None

        ath = data.get("athlete", {})
        headshot_obj = ath.get("headshot", {})
        if isinstance(headshot_obj, dict):
            headshot = headshot_obj.get("href", f"https://a.espncdn.com/i/headshots/{league}/players/full/{athlete_id}.png")
        elif isinstance(headshot_obj, str) and headshot_obj.startswith("http"):
            headshot = headshot_obj
        else:
            headshot = f"https://a.espncdn.com/i/headshots/{league}/players/full/{athlete_id}.png"
        
        position = ath.get("position", {}).get("displayName", "")
        team_name = ath.get("team", {}).get("displayName", "")
        jersey = ath.get("jersey", "")
        height = ath.get("displayHeight", "")
        weight = ath.get("displayWeight", "")
        experience = ath.get("experience", {}).get("years", 0)

        return {
            "id": athlete_id,
            "name": ath.get("displayName", "Atleta"),
            "headshot": headshot,
            "position": position,
            "team_name": team_name,
            "jersey": jersey,
            "height": height,
            "weight": weight,
            "experience": experience,
            "sport": sport,
            "league": league
        }

    # Full League Division Standings Table Endpoint 💬 (.../standings)
    def get_full_standings(self, sport: str, league: str) -> List[Dict[str, Any]]:
        url = f"{self.V2_STANDINGS_URL}/{sport}/{league}/standings"
        data = self._fetch_json(url)
        if not data:
            return []

        divisions = []
        def parse_node(node, name_prefix=''):
            c_name = node.get('name', node.get('shortName', ''))
            full_name = f"{name_prefix} {c_name}".strip()
            
            entries = node.get('standings', {}).get('entries', [])
            if entries:
                teams_list = []
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    t = entry.get('team', {})
                    if not isinstance(t, dict):
                        t = {}
                    t_name = t.get('displayName', t.get('name', ''))
                    t_logo = ''
                    logos = t.get('logos', [])
                    if isinstance(logos, list) and len(logos) > 0 and isinstance(logos[0], dict):
                        t_logo = logos[0].get('href', '')
                    t_id = t.get('id', '')
                    
                    stats = {}
                    for s in entry.get('stats', []):
                        if isinstance(s, dict):
                            s_key = s.get('name', s.get('type', ''))
                            if s_key:
                                stats[s_key] = s.get('displayValue', '0')
                        
                    teams_list.append({
                        'id': t_id,
                        'name': t_name,
                        'logo': t_logo,
                        'wins': stats.get('wins', stats.get('W', '0')),
                        'losses': stats.get('losses', stats.get('L', '0')),
                        'win_pct': stats.get('winPercent', stats.get('pct', '.000')),
                        'games_behind': stats.get('gamesBehind', stats.get('GB', '-')),
                        'streak': stats.get('streak', stats.get('strk', '-')),
                        'home_record': stats.get('Home', stats.get('home', '-')),
                        'away_record': stats.get('Road', stats.get('road', '-')),
                        'diff': stats.get('pointDifferential', stats.get('runDifferential', '-'))
                    })
                divisions.append({'name': full_name, 'teams': teams_list})
                
            for child in node.get('children', []):
                parse_node(child, full_name)

        for conf in data.get('children', []):
            parse_node(conf)

        return divisions

    def get_standings(self, sport: str, league: str) -> List[Dict[str, Any]]:
        return self.get_full_standings(sport, league)
