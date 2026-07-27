import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, jsonify, redirect, make_response
from espn_client import ESPNClient
from config import ACTIVE_LEAGUES
from formatter import PostFormatter, translate_text, format_datetime_et
from telegram_publisher import TelegramPublisher

app = Flask(__name__, template_folder="templates", static_folder="static")
espn = ESPNClient()
publisher = TelegramPublisher()
ET_ZONE = ZoneInfo("America/New_York")

# UI Labels without any emojis (Icons are handled strictly via FontAwesome vector icons)
UI_LABELS = {
    "en": {
        "lang_code": "en",
        "nav_games": "Live Games",
        "nav_news": "News",
        "nav_standings": "Standings",
        "nav_leaders": "Leaders",
        "nav_h2h": "H2H",
        "nav_videos": "Videos",
        "nav_telegram": "Telegram",
        "switch_lang_label": "Español",
        "switch_lang_target": "es",
        "hero_title": "GamePulse Sports Portal",
        "hero_desc": "Real-time sports scores, full news articles, stat leaders, videos and team matchups.",
        "search_placeholder": "Search by team, player, or keyword...",
        "btn_yesterday": "Yesterday",
        "btn_today": "Today",
        "btn_tomorrow": "Tomorrow",
        "all_sports": "All Sports",
        "section_games": "Scores & Live Games",
        "badge_live": "LIVE NOW",
        "section_news": "Full Coverage & Articles",
        "section_news_page": "Latest Breaking Sports News & Coverage",
        "footer_rights": "© 2026 GamePulse Sports Media. Real-time sports coverage.",
        "view_details": "View Details →",
        "final": "Final",
        "byline_prefix": "By"
    },
    "es": {
        "lang_code": "es",
        "nav_games": "Partidos",
        "nav_news": "Noticias",
        "nav_standings": "Posiciones",
        "nav_leaders": "Líderes",
        "nav_h2h": "H2H",
        "nav_videos": "Videos",
        "nav_telegram": "Telegram",
        "switch_lang_label": "English",
        "switch_lang_target": "en",
        "hero_title": "Portal Deportivo GamePulse",
        "hero_desc": "Toda la información deportiva en tiempo real. Marcadores en vivo, noticias completas y estadísticas.",
        "search_placeholder": "Buscar por equipo, jugador o palabra clave...",
        "btn_yesterday": "Ayer",
        "btn_today": "Hoy",
        "btn_tomorrow": "Mañana",
        "all_sports": "Todos los Deportes",
        "section_games": "Marcadores & Partidos",
        "badge_live": "EN VIVO Y EN DIRECTO",
        "section_news": "Noticias Completas & Redacción",
        "section_news_page": "Noticias Deportivas & Redacción en Vivo",
        "footer_rights": "© 2026 GamePulse Sports Media. Cobertura deportiva en tiempo real.",
        "view_details": "Ver Detalles →",
        "final": "Final",
        "byline_prefix": "Por"
    }
}

def get_current_lang():
    lang_param = request.args.get("lang", "").strip().lower()
    if lang_param in ["en", "es"]:
        return lang_param
    cookie_lang = request.cookies.get("gamepulse_lang", "").strip().lower()
    if cookie_lang in ["en", "es"]:
        return cookie_lang
    return "en"

@app.route("/")
def index():
    lang = get_current_lang()
    ui = UI_LABELS[lang]

    league_filter = request.args.get("league", "").strip().lower()
    search_query = request.args.get("q", "").strip().lower()
    date_param = request.args.get("date", "").strip()

    today_et = datetime.now(ET_ZONE)
    if not date_param:
        selected_date_str = today_et.strftime("%Y-%m-%d")
        espn_date_str = today_et.strftime("%Y%m%d")
    else:
        try:
            dt_obj = datetime.strptime(date_param, "%Y-%m-%d")
            selected_date_str = date_param
            espn_date_str = dt_obj.strftime("%Y%m%d")
        except Exception:
            selected_date_str = today_et.strftime("%Y-%m-%d")
            espn_date_str = today_et.strftime("%Y%m%d")

    yesterday_str = (today_et - timedelta(days=1)).strftime("%Y-%m-%d")
    today_str = today_et.strftime("%Y-%m-%d")
    tomorrow_str = (today_et + timedelta(days=1)).strftime("%Y-%m-%d")

    target_leagues = [l for l in ACTIVE_LEAGUES if l["league"] == league_filter] if league_filter else ACTIVE_LEAGUES

    all_games = []
    for league in target_leagues:
        events = espn.get_scoreboard(league["sport"], league["league"], dates=espn_date_str)
        for ev in events:
            if search_query:
                h_name = ev.get("home_team", {}).get("name", "").lower()
                a_name = ev.get("away_team", {}).get("name", "").lower()
                if search_query not in h_name and search_query not in a_name and search_query not in ev.get("name", "").lower():
                    continue
            all_games.append(ev)

    def game_priority_key(ev):
        state = ev.get("status_state", "pre")
        if state == "in":
            return 0
        elif state == "pre":
            return 1
        else:
            return 2

    all_games.sort(key=game_priority_key)

    resp = make_response(render_template(
        "index.html",
        ui=ui,
        lang=lang,
        games=all_games,
        active_league=league_filter,
        search_query=search_query,
        selected_date=selected_date_str,
        yesterday_date=yesterday_str,
        today_date=today_str,
        tomorrow_date=tomorrow_str
    ))
    resp.set_cookie("gamepulse_lang", lang, max_age=30*24*3600)
    return resp

@app.route("/buscar")
def search_view():
    lang = get_current_lang()
    ui = UI_LABELS[lang]
    query = request.args.get("q", "").strip()

    if not query:
        results = {"players": [], "teams": []}
    else:
        results = espn.search_global(query)

    resp = make_response(render_template(
        "search.html",
        ui=ui,
        lang=lang,
        query=query,
        players=results.get("players", []),
        teams=results.get("teams", [])
    ))
    resp.set_cookie("gamepulse_lang", lang, max_age=30*24*3600)
    return resp

@app.route("/noticias")
def news_view():
    lang = get_current_lang()
    ui = UI_LABELS[lang]

    league_filter = request.args.get("league", "").strip().lower()
    search_query = request.args.get("q", "").strip().lower()

    target_leagues = [l for l in ACTIVE_LEAGUES if l["league"] == league_filter] if league_filter else ACTIVE_LEAGUES

    all_news = []
    for league in target_leagues:
        articles = espn.get_news(league["sport"], league["league"], limit=6)
        for art in articles:
            if search_query:
                h_text = art.get("headline", "").lower()
                d_text = art.get("description", "").lower()
                if search_query not in h_text and search_query not in d_text:
                    continue
            if lang == "es":
                art["headline"] = translate_text(art["headline"], "Spanish")
                art["description"] = translate_text(art["description"], "Spanish")
            art["published"] = format_datetime_et(art["published"], lang)
            all_news.append(art)

    resp = make_response(render_template(
        "news.html",
        ui=ui,
        lang=lang,
        news=all_news,
        active_league=league_filter,
        search_query=search_query
    ))
    resp.set_cookie("gamepulse_lang", lang, max_age=30*24*3600)
    return resp

@app.route("/posiciones")
def standings_view():
    lang = get_current_lang()
    ui = UI_LABELS[lang]

    league_filter = request.args.get("league", "mlb").strip().lower()
    league_info = next((l for l in ACTIVE_LEAGUES if l["league"] == league_filter), ACTIVE_LEAGUES[0])
    
    standings_data = espn.get_full_standings(league_info["sport"], league_info["league"])
    resp = make_response(render_template("standings.html", ui=ui, lang=lang, standings=standings_data, active_league=league_filter))
    resp.set_cookie("gamepulse_lang", lang, max_age=30*24*3600)
    return resp

@app.route("/lideres")
def leaders_view():
    lang = get_current_lang()
    ui = UI_LABELS[lang]

    league_filter = request.args.get("league", "mlb").strip().lower()
    league_info = next((l for l in ACTIVE_LEAGUES if l["league"] == league_filter), ACTIVE_LEAGUES[0])
    sport = league_info["sport"]
    league = league_info["league"]

    # Fetch Overall General League Leaders (Home Runs, Hits, RBIs, AVG, Pitching, Points, etc.)
    general_categories = espn.get_general_league_leaders(sport, league)

    resp = make_response(render_template(
        "leaders.html",
        ui=ui,
        lang=lang,
        categories=general_categories,
        active_league=league_filter
    ))
    resp.set_cookie("gamepulse_lang", lang, max_age=30*24*3600)
    return resp

@app.route("/videos")
def videos_view():
    lang = get_current_lang()
    ui = UI_LABELS[lang]
    resp = make_response(render_template("videos.html", ui=ui, lang=lang))
    resp.set_cookie("gamepulse_lang", lang, max_age=30*24*3600)
    return resp

@app.route("/h2h")
def h2h_view():
    lang = get_current_lang()
    ui = UI_LABELS[lang]

    league_filter = request.args.get("league", "mlb").strip().lower()
    league_info = next((l for l in ACTIVE_LEAGUES if l["league"] == league_filter), ACTIVE_LEAGUES[0])
    sport = league_info["sport"]
    league = league_info["league"]

    teams = espn.get_teams(sport, league)

    t1_id = request.args.get("t1", "")
    t2_id = request.args.get("t2", "")

    if not t1_id and teams:
        t1_id = str(teams[0]["id"])
    if not t2_id and len(teams) > 1:
        t2_id = str(teams[1]["id"])
    elif not t2_id and teams:
        t2_id = str(teams[0]["id"])

    t1_data = espn.get_team_detail(sport, league, t1_id) if t1_id else None
    t2_data = espn.get_team_detail(sport, league, t2_id) if t2_id else None

    resp = make_response(render_template("h2h.html", ui=ui, lang=lang, teams=teams, t1=t1_data, t2=t2_data, sport=sport, league=league, active_league=league))
    resp.set_cookie("gamepulse_lang", lang, max_age=30*24*3600)
    return resp

@app.route("/noticia/<article_id>")
def article_detail(article_id):
    lang = get_current_lang()
    ui = UI_LABELS[lang]

    sport = request.args.get("sport", "baseball")
    league = request.args.get("league", "mlb")

    target_article = espn.get_article_by_id(article_id, sport, league)

    if not target_article:
        target_article = {
            "id": article_id,
            "headline": "GamePulse Sports Article",
            "description": "Full details of the sports alert.",
            "published": "",
            "byline": "Redacción ESPN",
            "images": [],
            "sport": sport,
            "league": league
        }

    raw_paragraphs = espn.get_full_article_content(target_article)
    translated_paragraphs = []
    for p in raw_paragraphs:
        if lang == "es":
            translated_paragraphs.append(translate_text(p, "Spanish"))
        else:
            translated_paragraphs.append(p)

    if lang == "es":
        target_article["headline"] = translate_text(target_article.get("headline", ""), "Spanish")
        target_article["description"] = translate_text(target_article.get("description", ""), "Spanish")

    target_article["published"] = format_datetime_et(target_article.get("published", ""), lang)

    resp = make_response(render_template("article.html", ui=ui, lang=lang, article=target_article, paragraphs=translated_paragraphs))
    # Prevent browser caching of news article pages so clicking a new link in Telegram always loads the fresh article
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    resp.set_cookie("gamepulse_lang", lang, max_age=30*24*3600)
    return resp

@app.route("/partido/<event_id>")
def match_detail(event_id):
    lang = get_current_lang()
    ui = UI_LABELS[lang]

    sport = request.args.get("sport", "baseball")
    league = request.args.get("league", "mlb")

    summary = espn.get_game_summary(sport, league, event_id)

    target_event = summary.get("event_info") if summary and summary.get("event_info") else None

    if not target_event:
        events = espn.get_scoreboard(sport, league)
        for ev in events:
            if str(ev["id"]) == str(event_id):
                target_event = ev
                break

    if not target_event:
        target_event = {
            "id": event_id,
            "league": league,
            "sport": sport,
            "status_detail": "Scheduled / Live",
            "home_team": {"id": "", "name": "Home Team", "score": "0", "logo": "", "record": ""},
            "away_team": {"id": "", "name": "Away Team", "score": "0", "logo": "", "record": ""}
        }

    odds = summary.get("odds", {}) if summary else {}
    lineups = summary.get("lineups", {}) if summary else {}
    decisions = summary.get("decisions", {}) if summary else {}
    boxscore_tables = summary.get("boxscore_tables", {}) if summary else {}
    plays = summary.get("plays", []) if summary else []

    resp = make_response(render_template("match.html", ui=ui, lang=lang, event=target_event, summary=summary, odds=odds, lineups=lineups, decisions=decisions, boxscore_tables=boxscore_tables, plays=plays))
    resp.set_cookie("gamepulse_lang", lang, max_age=30*24*3600)
    return resp

@app.route("/equipo/")
@app.route("/equipo/<team_id>")
def team_detail(team_id=None):
    if not team_id:
        return redirect("/")
        
    lang = get_current_lang()
    ui = UI_LABELS[lang]

    sport = request.args.get("sport", "baseball")
    league = request.args.get("league", "mlb")
    
    team_data = espn.get_team_detail(sport, league, team_id)
    if not team_data:
        team_data = {
            "id": team_id,
            "name": "Sports Team",
            "abbreviation": "",
            "logo": "",
            "color": "1C1C1E",
            "record": "N/A",
            "standing_summary": "",
            "roster": [],
            "sport": sport,
            "league": league
        }

    resp = make_response(render_template("team.html", ui=ui, lang=lang, team=team_data))
    resp.set_cookie("gamepulse_lang", lang, max_age=30*24*3600)
    return resp

@app.route("/jugador/")
@app.route("/jugador/<athlete_id>")
def athlete_detail(athlete_id=None):
    if not athlete_id:
        return redirect("/")
        
    lang = get_current_lang()
    ui = UI_LABELS[lang]

    sport = request.args.get("sport", "baseball")
    league = request.args.get("league", "mlb")
    
    ath_data = espn.get_athlete_detail(sport, league, athlete_id)
    if not ath_data:
        ath_data = {
            "id": athlete_id,
            "name": "Pro Athlete",
            "headshot": f"https://a.espncdn.com/i/headshots/{league}/players/full/{athlete_id}.png",
            "position": "Athlete",
            "team_name": "GamePulse League",
            "jersey": "",
            "height": "",
            "weight": "",
            "experience": 0,
            "sport": sport,
            "league": league
        }

    resp = make_response(render_template("athlete.html", ui=ui, lang=lang, athlete=ath_data))
    resp.set_cookie("gamepulse_lang", lang, max_age=30*24*3600)
    return resp

@app.route("/api/publish_to_telegram", methods=["POST"])
def publish_to_telegram_endpoint():
    data = request.get_json() or {}
    item_type = data.get("type", "news")
    item_id = data.get("id", "")
    sport = data.get("sport", "baseball")
    league_code = data.get("league", "mlb")

    league_info = next((l for l in ACTIVE_LEAGUES if l["league"] == league_code), ACTIVE_LEAGUES[0])

    try:
        if item_type == "news":
            articles = espn.get_news(sport, league_code, limit=15)
            target = next((a for a in articles if str(a["id"]) == str(item_id)), None)
            if not target and articles:
                target = articles[0]
            if target:
                msg_es, msg_en, img_url = PostFormatter.format_news(target, league_info)
                publisher.publish_bilingual(msg_es, msg_en, img_url)
                return jsonify({"status": "success", "message": "Noticia publicada con éxito en Telegram 🚀"})

        elif item_type == "match":
            events = espn.get_scoreboard(sport, league_code)
            target_ev = next((e for e in events if str(e["id"]) == str(item_id)), None)
            if target_ev:
                summary = espn.get_game_summary(sport, league_code, item_id)
                msg_es, msg_en, img_url = PostFormatter.format_summary(summary or {}, target_ev, league_info)
                publisher.publish_bilingual(msg_es, msg_en, img_url)
                return jsonify({"status": "success", "message": "Resumen de partido publicado con éxito en Telegram 🚀"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "error", "message": "No se encontró el elemento a publicar."}), 404

@app.route("/api/scoreboard")
def api_scoreboard():
    lang = get_current_lang()
    date_str = request.args.get("date", "").strip()
    league_filter = request.args.get("league", "all").strip().lower()

    if not date_str:
        now_et = datetime.now(ET_ZONE)
        date_str = now_et.strftime("%Y-%m-%d")

    target_leagues = ACTIVE_LEAGUES if league_filter == "all" else [l for l in ACTIVE_LEAGUES if l["league"] == league_filter]

    all_games = []
    for league in target_leagues:
        events = espn.get_scoreboard(league["sport"], league["league"], date_str)
        for ev in events:
            date_utc = ev.get("date", "")
            ev["formatted_date"] = format_datetime_et(date_utc, lang) if date_utc else ""
            ev["sport"] = league["sport"]
            ev["league"] = league["league"]
            ev["league_name"] = league["name"] if lang == "es" else league["name_en"]
            ev["league_emoji"] = league["icon"]
            all_games.append(ev)

    return jsonify({
        "status": "success",
        "date": date_str,
        "games": all_games
    })

@app.route("/api/match/<event_id>")
def api_match_detail(event_id):
    lang = get_current_lang()
    sport = request.args.get("sport", "baseball").strip().lower()
    league = request.args.get("league", "mlb").strip().lower()

    summary_data = espn.get_game_summary(sport, league, event_id)
    if not summary_data:
        return jsonify({"status": "error", "message": "Game details not found"}), 404

    events = espn.get_scoreboard(sport, league)
    target_event = next((e for e in events if str(e.get("id")) == str(event_id)), None)

    date_utc = summary_data.get("header", {}).get("competitions", [{}])[0].get("date", "")
    summary_data["formatted_date"] = format_datetime_et(date_utc, lang) if date_utc else ""

    return jsonify({
        "status": "success",
        "event": target_event,
        "summary": summary_data
    })

def run_web_server():
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    run_web_server()
