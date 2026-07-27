import json
import urllib.request
import urllib.parse
import re
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

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

    def get_article_by_id(self, article_id: str, sport: str = "baseball", league: str = "mlb") -> Optional[Dict[str, Any]]:
        target_id_str = str(article_id).strip()
        if not target_id_str:
            return None

        # 1. Search target sport/league first with limit=50
        articles = self.get_news(sport, league, limit=50)
        for art in articles:
            if str(art.get("id")) == target_id_str:
                return art

        # 2. Search across all other active leagues if not found in primary league
        leagues = [("baseball", "mlb"), ("basketball", "nba"), ("football", "nfl"), ("hockey", "nhl")]
        for s, l in leagues:
            if s == sport and l == league:
                continue
            other_articles = self.get_news(s, l, limit=25)
            for art in other_articles:
                if str(art.get("id")) == target_id_str:
                    return art

        return None

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

        odds_obj = None
        if summary_data and "pickcenter" in summary_data and len(summary_data["pickcenter"]) > 0:
            odds_obj = summary_data["pickcenter"][0]
        elif "odds" in competition and len(competition["odds"]) > 0:
            odds_obj = competition["odds"][0]

        if not odds_obj:
            return odds_info

        # 1. Details & Spread
        details = odds_obj.get("details", "N/A")
        if details == "N/A" or not details:
            details = str(odds_obj.get("spread", "N/A"))
        odds_info["details"] = details
        odds_info["spread"] = str(odds_obj.get("spread", details))

        # 2. Over / Under Total
        ou = odds_obj.get("overUnder")
        if ou is None:
            ou = odds_obj.get("total", {}).get("over", {}).get("close", {}).get("line", "N/A")
        ou_str = str(ou) if ou is not None else "N/A"
        if ou_str.startswith("o"):
            ou_str = ou_str[1:]
        odds_info["over_under"] = ou_str

        # 3. Moneyline Home & Away
        ml_home = "N/A"
        ml_away = "N/A"

        # Check moneyline object in ESPN structure
        ml_dict = odds_obj.get("moneyline", {})
        if isinstance(ml_dict, dict) and ml_dict:
            ml_home = ml_dict.get("home", {}).get("close", {}).get("odds") or ml_dict.get("home", {}).get("open", {}).get("odds") or "N/A"
            ml_away = ml_dict.get("away", {}).get("close", {}).get("odds") or ml_dict.get("away", {}).get("open", {}).get("odds") or "N/A"

        # Fallback to homeTeamOdds / awayTeamOdds
        if ml_home == "N/A":
            ht_odds = odds_obj.get("homeTeamOdds", {})
            ml_home = str(ht_odds.get("moneyLine", ht_odds.get("summary", "N/A"))) if isinstance(ht_odds, dict) else "N/A"

        if ml_away == "N/A":
            at_odds = odds_obj.get("awayTeamOdds", {})
            ml_away = str(at_odds.get("moneyLine", at_odds.get("summary", "N/A"))) if isinstance(at_odds, dict) else "N/A"

        odds_info["moneyline_home"] = str(ml_home)
        odds_info["moneyline_away"] = str(ml_away)

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
                        pos_obj = ath.get("position", {}) or ath.get("athlete", {}).get("position", {})
                        position = pos_obj.get("abbreviation", "") if isinstance(pos_obj, dict) else ""
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
                                "position": position,
                                "stats": stats_vals
                            })

                            # Batting stats (Scored by performance: RBIs, HRs, Hits, Runs)
                            if "H-AB" in labels and len(stats_vals) >= 6:
                                try:
                                    h_ab = stats_vals[0]
                                    h = float(stats_vals[3]) if len(stats_vals) > 3 else 0
                                    rbi = float(stats_vals[4]) if len(stats_vals) > 4 else 0
                                    hr = float(stats_vals[5]) if len(stats_vals) > 5 else 0
                                    r = float(stats_vals[2]) if len(stats_vals) > 2 else 0
                                    score = rbi * 3.5 + hr * 4.0 + h * 2.0 + r * 1.5
                                    if h_ab not in ["0-4", "0-3", "0-2", "0-1", "0-5"] and score > 0:
                                        detail_str = h_ab
                                        if rbi > 0: detail_str += f", {int(rbi)} RBI"
                                        if hr > 0: detail_str += f", {int(hr)} HR"
                                        by_team[team_abbrev].append((score, {
                                            "id": ath_id,
                                            "team": team_abbrev,
                                            "category": "Bateo",
                                            "athlete": ath_name,
                                            "stats": detail_str
                                        }))
                                except Exception:
                                    pass

                            # Pitching stats (Scored by IP, Ks, ERs)
                            elif "IP" in labels and len(stats_vals) >= 6:
                                try:
                                    ip = float(stats_vals[0])
                                    er = float(stats_vals[3])
                                    so = float(stats_vals[5])
                                    score = ip * 3.0 + so * 2.0 - er * 3.0
                                    if ip >= 1.0 and score > 0:
                                        by_team[team_abbrev].append((score, {
                                            "id": ath_id,
                                            "team": team_abbrev,
                                            "category": "Pitcheo",
                                            "athlete": ath_name,
                                            "stats": f"{ip} IP, {int(so)} K, {int(er)} CL"
                                        }))
                                except Exception:
                                    pass

                    team_categories.append({
                        "name": cat_name,
                        "labels": labels,
                        "athletes": athletes_list
                    })

                boxscore_tables[side] = {
                    "team_name": team_name,
                    "categories": team_categories
                }

        # Select Top 2 Ranked Performers from BOTH teams
        team_keys = list(by_team.keys())
        if len(team_keys) >= 2:
            team1, team2 = team_keys[0], team_keys[1]
            by_team[team1].sort(key=lambda x: x[0], reverse=True)
            by_team[team2].sort(key=lambda x: x[0], reverse=True)
            
            t1_list = [item[1] for item in by_team[team1][:2]]
            t2_list = [item[1] for item in by_team[team2][:2]]
            
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

    # Overall General League Leaders (Top 10 Qualified Regular Season Leaders from ESPN Core API)
    def get_general_league_leaders(self, sport: str, league: str) -> List[Dict[str, Any]]:
        url = f"https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/seasons/2026/types/2/leaders"
        data = self._fetch_json(url)
        general_categories = []

        if data and "categories" in data:
            refs_to_fetch = set()
            for cat in data.get("categories", []):
                for item in cat.get("leaders", [])[:10]:
                    ath_ref = item.get("athlete", {}).get("$ref", "")
                    team_ref = item.get("team", {}).get("$ref", "")
                    if ath_ref: refs_to_fetch.add(ath_ref.replace("http://", "https://"))
                    if team_ref: refs_to_fetch.add(team_ref.replace("http://", "https://"))

            cache = {}
            if refs_to_fetch:
                try:
                    with ThreadPoolExecutor(max_workers=30) as executor:
                        results = executor.map(lambda r: (r, self._fetch_json(r)), list(refs_to_fetch))
                        for r, res in results:
                            if res: cache[r] = res
                except Exception as e:
                    logger.warning(f"Error fetching leaders refs concurrently: {e}")

            for cat in data.get("categories", []):
                cat_name = cat.get("displayName", cat.get("name", "Estadísticas"))
                leaders = []
                for item in cat.get("leaders", [])[:10]:
                    ath_ref = item.get("athlete", {}).get("$ref", "").replace("http://", "https://")
                    team_ref = item.get("team", {}).get("$ref", "").replace("http://", "https://")
                    val_raw = item.get("value", "")
                    disp_val = item.get("displayValue", "")

                    ath_id = ath_ref.split("/")[-1].split("?")[0] if ath_ref else ""
                    ath_data = cache.get(ath_ref, {})
                    ath_name = ath_data.get("displayName", ath_data.get("fullName", "Atleta")) if isinstance(ath_data, dict) else "Atleta"
                    headshot = f"https://a.espncdn.com/i/headshots/{league}/players/full/{ath_id}.png"

                    team_data = cache.get(team_ref, {})
                    team_abbrev = team_data.get("abbreviation", league.upper()) if isinstance(team_data, dict) else league.upper()

                    cleaned_val = clean_stat_value(cat_name, disp_val, val_raw)

                    if ath_id and ath_name:
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
                        "leaders": leaders
                    })

        if general_categories:
            return general_categories

        # Fallback to site API if core API is unavailable
        fallback_url = f"{self.BASE_URL}/{sport}/{league}/statistics?seasontype=2"
        fb_data = self._fetch_json(fallback_url)
        if fb_data and "stats" in fb_data:
            stats_obj = fb_data["stats"]
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
            clean_date = dates.replace("-", "").strip()
            url += f"?dates={clean_date}"
            
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
        home_id = str(event_home.get("id", ""))
        away_id = str(event_away.get("id", ""))
        home_name = event_home.get("short_name", event_home.get("name", "Local"))
        away_name = event_away.get("short_name", event_away.get("name", "Visitante"))
        home_logo = event_home.get("logo", "")
        away_logo = event_away.get("logo", "")

        parsed_plays = []
        for p in plays:
            p_text = p.get("text", "").strip()
            per_obj = p.get("period", {}) if isinstance(p.get("period"), dict) else {}
            per_type = per_obj.get("type", "")
            per_num = per_obj.get("number", "")
            per_disp = per_obj.get("displayValue", "")
            p_clock = p.get("clock", {}).get("displayValue", "")

            # Build bilingual period label (Top = Parte Alta, Bottom = Parte Baja)
            if per_type == "Top":
                period_es = f"🔺 Parte Alta ({per_num}º Inning)"
                period_en = f"🔺 Top ({per_disp})"
            elif per_type == "Bottom":
                period_es = f"🔻 Parte Baja ({per_num}º Inning)"
                period_en = f"🔻 Bottom ({per_disp})"
            elif per_type == "Mid":
                period_es = f"⏱️ Mitad del {per_num}º Inning"
                period_en = f"⏱️ Mid {per_disp}"
            elif per_type == "End":
                period_es = f"🏁 Fin del {per_num}º Inning"
                period_en = f"🏁 End {per_disp}"
            else:
                period_es = per_disp
                period_en = per_disp

            # Detect if play is an Inning Header (e.g. "Top of the 1st inning")
            p_type_code = p.get("type", {}).get("type", "") if isinstance(p.get("type"), dict) else ""
            p_text_lower = p_text.lower()
            is_header = p_type_code in ["start-inning", "end-inning"] or any(k in p_text_lower for k in ["top of the", "bottom of the", "end of the", "mid "])

            # Translate text for inning headers
            text_es = p_text
            if is_header:
                m = re.search(r'(top|bottom|end)\s+of\s+the\s+(\d+)(st|nd|rd|th)\s+inning', p_text_lower)
                if m:
                    half, num, _ = m.groups()
                    half_str = "🔺 Inicio: Parte Alta" if half == "top" else ("🔻 Inicio: Parte Baja" if half == "bottom" else "🏁 Fin")
                    text_es = f"{half_str} del {num}º Inning"

            is_scoring = p.get("scoringPlay", False) or p.get("scoreValue", 0) > 0 or "scored" in p_text_lower or "homered" in p_text_lower or "grand slam" in p_text_lower

            p_team_id = str(p.get("team", {}).get("id", "")) if isinstance(p.get("team"), dict) else ""
            team_info = None
            if p_team_id == home_id:
                team_info = {"name": home_name, "logo": home_logo, "side": "home"}
            elif p_team_id == away_id:
                team_info = {"name": away_name, "logo": away_logo, "side": "away"}

            if p_text:
                parsed_plays.append({
                    "id": p.get("id", ""),
                    "text": p_text,
                    "text_es": text_es,
                    "period": period_en,
                    "period_es": period_es,
                    "clock": p_clock,
                    "scoringPlay": is_scoring,
                    "scoring": is_scoring,
                    "is_header": is_header,
                    "team": team_info
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

        # Head Coach / Manager
        coach_name = ""
        coach_arr = t.get("coaches", []) or t.get("coach", [])
        if isinstance(coach_arr, list) and coach_arr:
            c = coach_arr[0]
            if isinstance(c, dict):
                coach_name = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip() or c.get("displayName", "")

        # Detailed Records (Overall, Home, Away, Streak, Differential, Points For/Against)
        record_info = {
            "summary": "",
            "home": "",
            "away": "",
            "win_pct": "",
            "streak": "",
            "diff": "",
            "pf": "",
            "pa": ""
        }
        if t.get("record") and "items" in t["record"]:
            for item in t["record"]["items"]:
                rec_type = item.get("type", "")
                summary = item.get("summary", "")
                stats_list = item.get("stats", [])
                
                if rec_type == "total":
                    record_info["summary"] = summary
                    for st in stats_list:
                        s_name = st.get("name", "")
                        s_val = st.get("value")
                        if s_name == "winPercent" and s_val is not None:
                            record_info["win_pct"] = f"{float(s_val):.3f}".lstrip("0")
                        elif s_name == "streak" and s_val is not None:
                            val_int = int(s_val)
                            record_info["streak"] = f"W{val_int}" if val_int > 0 else (f"L{abs(val_int)}" if val_int < 0 else "-")
                        elif s_name == "pointDifferential" and s_val is not None:
                            val_int = int(s_val)
                            record_info["diff"] = f"+{val_int}" if val_int > 0 else str(val_int)
                        elif s_name == "pointsFor" and s_val is not None:
                            record_info["pf"] = str(int(s_val))
                        elif s_name == "pointsAgainst" and s_val is not None:
                            record_info["pa"] = str(int(s_val))
                elif rec_type == "home":
                    record_info["home"] = summary
                elif rec_type in ["road", "away"]:
                    record_info["away"] = summary

        # Fetch Official Roster
        roster_url = f"{self.BASE_URL}/{sport}/{league}/teams/{team_id}/roster"
        roster_data = self._fetch_json(roster_url)
        athletes = []
        if not coach_name and roster_data and "coach" in roster_data and roster_data["coach"]:
            c = roster_data["coach"][0] if isinstance(roster_data["coach"], list) else roster_data["coach"]
            if isinstance(c, dict):
                coach_name = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()

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
                        position = pos_obj.get("abbreviation", pos_obj.get("displayName", pos_group_name)) if isinstance(pos_obj, dict) else str(pos_group_name)
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

        # Fetch Team Schedule & Results
        schedule = []
        sched_url = f"{self.BASE_URL}/{sport}/{league}/teams/{team_id}/schedule"
        sched_data = self._fetch_json(sched_url)
        if sched_data and "events" in sched_data:
            for ev in sched_data.get("events", []):
                ev_id = str(ev.get("id"))
                comps = ev.get("competitions", [{}])[0]
                date_utc = ev.get("date", "")
                
                home_c = None
                away_c = None
                for c in comps.get("competitors", []):
                    if c.get("homeAway") == "home": home_c = c
                    else: away_c = c
                    
                is_home = str(home_c.get("id")) == str(team_id) if home_c else True
                team_c = home_c if is_home else away_c
                opp_c = away_c if is_home else home_c
                
                opp_name = opp_c.get("team", {}).get("displayName", "") if opp_c else "Opponent"
                opp_logo = opp_c.get("team", {}).get("logo", "") if opp_c else ""
                
                status_type = comps.get("status", {}).get("type", {}).get("name", "")
                status_detail = comps.get("status", {}).get("type", {}).get("shortDetail", "")
                is_completed = status_type == "STATUS_FINAL"
                win = False
                score_str = ""
                
                if is_completed and team_c and opp_c:
                    t_val = int(team_c.get("score", {}).get("value", 0))
                    o_val = int(opp_c.get("score", {}).get("value", 0))
                    win = team_c.get("winner", False) or (t_val > o_val)
                    score_str = f"{t_val}-{o_val}"
                    
                schedule.append({
                    "id": ev_id,
                    "date": date_utc,
                    "is_home": is_home,
                    "prefix": "vs" if is_home else "@",
                    "opp_name": opp_name,
                    "opp_logo": opp_logo,
                    "is_completed": is_completed,
                    "win": win,
                    "score_str": score_str,
                    "status_detail": status_detail
                })

        # Fetch League Division Standings Table for Team
        division_standings = []
        try:
            all_standings = self.get_full_standings(sport, league)
            for group in all_standings:
                t_list = group.get("teams", [])
                if any(str(t_item.get("id")) == str(team_id) for t_item in t_list):
                    division_standings = t_list
                    break
        except Exception:
            pass

        return {
            "id": t.get("id"),
            "name": t.get("displayName"),
            "abbreviation": t.get("abbreviation"),
            "logo": logo,
            "color": t.get("color", "1C1C1E"),
            "record": record_info,
            "standing_summary": t.get("standingSummary", ""),
            "coach": coach_name,
            "roster": athletes,
            "schedule": schedule,
            "standings": division_standings,
            "sport": sport,
            "league": league
        }

    # Full Athlete Profile Endpoint (Bio, Season Stats, Highlights Banner, Recent Games Log)
    def get_athlete_detail(self, sport: str, league: str, athlete_id: str) -> Optional[Dict[str, Any]]:
        core_url = f"https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/athletes/{athlete_id}"
        overview_url = f"https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{athlete_id}/overview"
        stats_url = f"https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{athlete_id}/stats"
        gamelog_url = f"https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{athlete_id}/gamelog"

        core = self._fetch_json(core_url) or {}
        overview = self._fetch_json(overview_url) or {}
        stats_data = self._fetch_json(stats_url) or {}
        gamelog = self._fetch_json(gamelog_url) or {}

        if not core and not overview and not gamelog:
            return None

        # Basic Info & Bio
        name = core.get("displayName", core.get("fullName", "Atleta"))
        jersey = core.get("jersey", "")
        pos = core.get("position", {}).get("displayName", "")
        ht = core.get("displayHeight", "")
        wt = core.get("displayWeight", "")
        dob = core.get("dateOfBirth", "").split("T")[0] if core.get("dateOfBirth") else ""
        age = str(core.get("age", ""))
        
        bats_val = core.get("bats", {})
        bats = bats_val.get("displayValue", "") if isinstance(bats_val, dict) else str(bats_val or "")
        
        throws_val = core.get("throws", {})
        throws = throws_val.get("displayValue", "") if isinstance(throws_val, dict) else str(throws_val or "")
        
        bplace_obj = core.get("birthPlace", {}) if isinstance(core.get("birthPlace"), dict) else {}
        city = bplace_obj.get("city", "")
        state = bplace_obj.get("state", "")
        country = bplace_obj.get("country", "")
        if city and state:
            birthplace = f"{city}, {state}"
        elif city and country:
            birthplace = f"{city}, {country}"
        else:
            birthplace = city or state or country or ""

        team_ref = core.get("team", {}).get("$ref", "") if isinstance(core.get("team"), dict) else ""
        team_name = ""
        team_logo = ""
        if team_ref:
            team_data = self._fetch_json(team_ref.replace("http://", "https://"))
            if team_data and isinstance(team_data, dict):
                team_name = team_data.get("displayName", "")
                logos = team_data.get("logos", [])
                if isinstance(logos, list) and len(logos) > 0 and isinstance(logos[0], dict):
                    team_logo = logos[0].get("href", "")

        # Headshot
        headshot_obj = core.get("headshot", {})
        if isinstance(headshot_obj, dict):
            headshot = headshot_obj.get("href", f"https://a.espncdn.com/i/headshots/{league}/players/full/{athlete_id}.png")
        elif isinstance(headshot_obj, str) and headshot_obj.startswith("http"):
            headshot = headshot_obj
        else:
            headshot = f"https://a.espncdn.com/i/headshots/{league}/players/full/{athlete_id}.png"

        # Highlights & Season Table from Overview (Primary for 100% Real-Time Sync with ESPN.com Overview tab)
        st_obj = overview.get("statistics", {}) if isinstance(overview, dict) else {}
        stats_display_name = st_obj.get("displayName", "2026 Season Stats")
        stats_labels = st_obj.get("labels", [])
        
        season_rows = []
        for split in st_obj.get("splits", []):
            if isinstance(split, dict):
                season_rows.append({"title": split.get("displayName", ""), "stats": split.get("stats", [])})

        # Fetch OPS / ERA from stats_data for banner
        ops_val = ".000"
        era_val = "0.00"
        if isinstance(stats_data, dict):
            for cat in stats_data.get("categories", []):
                if not isinstance(cat, dict): continue
                lbls = cat.get("labels", [])
                for stat_row in cat.get("statistics", []):
                    if not isinstance(stat_row, dict): continue
                    season_obj = stat_row.get("season", {})
                    if str(season_obj.get("year", "")) == "2026" if isinstance(season_obj, dict) else False:
                        val_map = dict(zip(lbls, stat_row.get("stats", [])))
                        if "OPS" in val_map and val_map["OPS"]:
                            ops_val = val_map["OPS"]
                        if "ERA" in val_map and val_map["ERA"]:
                            era_val = val_map["ERA"]

        # Calculate / Build Highlights Banner
        reg_row = next((s for s in st_obj.get("splits", []) if isinstance(s, dict) and s.get("displayName") == "Regular Season"), None)
        val_map = dict(zip(stats_labels, reg_row.get("stats", []))) if reg_row else {}

        h_count = float(val_map.get("H", 0)) if val_map.get("H") else 0
        ab_count = float(val_map.get("AB", 0)) if val_map.get("AB") else 0
        avg_val = f"{h_count / ab_count:.3f}".lstrip("0") if ab_count > 0 else val_map.get("AVG", ".000")

        if "AVG" in stats_labels or "AB" in stats_labels:
            highlights = [
                {"label": "AVG", "value": avg_val},
                {"label": "HR", "value": val_map.get("HR", "0")},
                {"label": "RBI", "value": val_map.get("RBI", "0")},
                {"label": "OPS", "value": ops_val}
            ]
        else:
            highlights = [
                {"label": "ERA", "value": era_val},
                {"label": "W", "value": val_map.get("W", "0")},
                {"label": "SO", "value": val_map.get("SO", "0")},
                {"label": "WHIP", "value": val_map.get("WHIP", "0.00")}
            ]

        # Fallback to stats_data if overview didn't return rows
        if not season_rows and isinstance(stats_data, dict):
            categories = stats_data.get("categories", [])
            main_cat = categories[0] if isinstance(categories, list) and len(categories) > 0 else {}
            stats_display_name = main_cat.get("displayName", "2026 Season Stats")
            stats_labels = main_cat.get("labels", [])
            if main_cat and isinstance(main_cat.get("statistics"), list):
                for stat_row in main_cat["statistics"]:
                    if not isinstance(stat_row, dict): continue
                    season_obj = stat_row.get("season", {})
                    s_year = str(season_obj.get("year", season_obj.get("displayName", ""))) if isinstance(season_obj, dict) else ""
                    r_vals = stat_row.get("stats", [])
                    season_rows.append({"title": s_year, "stats": r_vals})

        # Recent Games Log
        gl_labels = gamelog.get("labels", ["AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO"])
        gl_events_dict = gamelog.get("events", {}) if isinstance(gamelog.get("events"), dict) else {}
        recent_games = []

        for st in gamelog.get("seasonTypes", []):
            if not isinstance(st, dict): continue
            for cat in st.get("categories", []):
                if not isinstance(cat, dict): continue
                for item in cat.get("events", []):
                    if not isinstance(item, dict): continue
                    ev_id = str(item.get("eventId", ""))
                    ev_info = gl_events_dict.get(ev_id, {})
                    
                    dt_raw = ev_info.get("gameDate", ev_info.get("eventDate", ""))
                    dt_fmt = ""
                    if dt_raw:
                        try:
                            dt_obj = datetime.fromisoformat(dt_raw.replace("Z", "+00:00"))
                            dt_fmt = dt_obj.strftime("%a %m/%d")
                        except Exception:
                            dt_fmt = dt_raw[:10]

                    opp = ev_info.get("opponent", {}).get("abbreviation", "") if isinstance(ev_info.get("opponent"), dict) else ""
                    at_vs = ev_info.get("atVs", "vs")
                    res_str = ev_info.get("gameResult", "")
                    row_stats = item.get("stats", [])

                    recent_games.append({
                        "date": dt_fmt,
                        "opponent": f"{at_vs} {opp}",
                        "result": res_str,
                        "stats": row_stats
                    })

        return {
            "id": athlete_id,
            "name": name,
            "headshot": headshot,
            "jersey": jersey,
            "position": pos,
            "height": ht,
            "weight": wt,
            "dob": dob,
            "age": age,
            "bats": bats,
            "throws": throws,
            "birthplace": birthplace,
            "team_name": team_name,
            "team_logo": team_logo,
            "highlights": highlights,
            "stats_display_name": stats_display_name,
            "stats_labels": stats_labels,
            "season_rows": season_rows,
            "gamelog_labels": gl_labels,
            "recent_games": recent_games[:10],
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

    # Unified Global Search for Players, Teams & Leagues 🔍
    def search_global(self, query: str) -> Dict[str, Any]:
        query_clean = query.strip()
        if not query_clean:
            return {"players": [], "teams": []}

        results = {"players": [], "teams": []}
        q_lower = query_clean.lower()

        leagues_list = [
            ("baseball", "mlb", "MLB"),
            ("basketball", "nba", "NBA"),
            ("football", "nfl", "NFL"),
            ("hockey", "nhl", "NHL")
        ]

        # 1. Search Teams across all 4 major leagues (MLB, NBA, NFL, NHL)
        for sport, league, l_name in leagues_list:
            try:
                teams = self.get_teams(sport, league)
                for t in teams:
                    t_name = t.get("name", "")
                    t_abbrev = t.get("abbreviation", "")
                    if q_lower in t_name.lower() or q_lower in t_abbrev.lower():
                        if not any(item["id"] == t.get("id") and item["league"] == league for item in results["teams"]):
                            results["teams"].append({
                                "id": t.get("id"),
                                "name": t_name,
                                "abbreviation": t_abbrev,
                                "logo": t.get("logo"),
                                "sport": sport,
                                "league": league,
                                "league_name": l_name
                            })
            except Exception as e:
                logger.warning(f"Error searching teams in {league}: {e}")

        # 2. Search Players / Athletes via ESPN Search V2 API
        try:
            url = f"https://site.api.espn.com/apis/search/v2?query={urllib.parse.quote(query_clean)}&limit=25"
            data = self._fetch_json(url)
            if isinstance(data, dict):
                for res_group in data.get("results", []):
                    if res_group.get("type") == "player":
                        for item in res_group.get("contents", []):
                            name = item.get("displayName", "")
                            sub = item.get("subtitle", "")
                            desc = item.get("description", "")
                            web_link = item.get("link", {}).get("web", "")
                            
                            ath_id_match = re.search(r'/id/(\d+)', web_link)
                            ath_id = ath_id_match.group(1) if ath_id_match else ""

                            league = "mlb"
                            sport = "baseball"
                            if "/nba/" in web_link: league, sport = "nba", "basketball"
                            elif "/nfl/" in web_link: league, sport = "nfl", "football"
                            elif "/nhl/" in web_link: league, sport = "nhl", "hockey"

                            if ath_id and name:
                                if not any(p["id"] == ath_id for p in results["players"]):
                                    results["players"].append({
                                        "id": ath_id,
                                        "name": name,
                                        "subtitle": sub or desc,
                                        "sport": sport,
                                        "league": league,
                                        "photo": f"https://a.espncdn.com/i/headshots/{league}/players/full/{ath_id}.png"
                                    })
        except Exception as e:
            logger.warning(f"Error searching players via ESPN Search API: {e}")

        return results
