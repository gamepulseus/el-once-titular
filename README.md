# ⚡ GamePulse - Automated Bilingual Telegram Sports Channels

GamePulse is a 100% automated service ($0 USD) that fetches real-time sports coverage from ESPN's public endpoints and publishes beautiful, formatted posts to two Telegram channels simultaneously: **Spanish (🇪🇸)** and **English (🇺🇸/🇬🇧)**.

---

## 🎯 Supported Pillars

1. **Flash Alerts ⚡ (Breaking News & Trades)**:
   - Endpoint: `.../news`
   - Real-time breaking news, headlines, descriptions, player injuries, and high-res event images.

2. **Game Preview 🔮 (Match Previews & Odds)**:
   - Endpoint: `.../scoreboard`
   - Upcoming matches, kick-off / tip-off times, team win/loss records, betting spread, favorite, and total over/under.

3. **Quick Analysis 📊 (Final Scores & Box Scores)**:
   - Endpoint: `.../summary?event={game_id}`
   - Post-game final score reports, star player/MVP performance leaders (points, yards, rebounds, goals), and period breakdowns.

4. **Community & Standings 💬 (Standings & Rankings)**:
   - Endpoint: `.../standings`
   - Conference/division standings, current team win streaks (e.g. W5, L2), records, and interactive polling questions for channel engagement.

---

## 🏆 Covered Sports & Leagues

- 🏀 **NBA** (`basketball/nba`)
- 🏈 **NFL** (`football/nfl`)
- ⚾ **MLB** (`baseball/mlb`)
- 🏒 **NHL** (`hockey/nhl`)
- 🏈 **NCAA Football** (`football/college-football`)
- 🏀 **NCAA Basketball** (`basketball/mens-college-basketball`)

---

## 🛠️ Setup & Installation

### 1. Requirements
- Python 3.10+ (No mandatory external dependencies required, built using Python standard library + sqlite3).
- Optional: `python-dotenv` for loading `.env` files.

### 2. Configure Telegram Credentials
1. Create a Telegram Bot via [@BotFather](https://t.me/BotFather) and copy your Bot Token.
2. Create two Telegram Channels (one for Spanish, one for English) and add your bot as an **Administrator** with post permissions in both channels.
3. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
4. Fill in your Telegram credentials in `.env`:
   ```ini
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   TELEGRAM_CHANNEL_ES=@TuCanalEnEspanol
   TELEGRAM_CHANNEL_EN=@YourEnglishChannel
   ```

---

## 🚀 Running GamePulse

### Dry-Run Test (Console Output without Telegram posting)
Fetch real live ESPN sports data and display formatted Spanish and English posts directly in your terminal:
```bash
python cli.py --dry-run
```

### Test Telegram Channel Ping
Send a quick ping message to verify your bot token and channel permissions:
```bash
python cli.py --test-telegram
```

### Run Continuous Auto-Publisher
Start the background loop to automatically poll and post news, game previews, box scores, and standings:
```bash
python main.py
```

### Run Unit Test Suite
```bash
python test_system.py
```

---

## 📁 Project Structure

```
gamepulse/
├── config.py             # System settings & active leagues
├── database.py           # SQLite deduplication & state tracking (gamepulse.db)
├── espn_client.py        # ESPN REST API wrapper (News, Scoreboard, Summary, Standings)
├── formatter.py          # Dual-language (ES/EN) post layout generator & sports dictionary
├── telegram_publisher.py # Telegram Bot HTTP API client (text + photos)
├── scheduler.py          # Periodic job runner & background task loop
├── main.py               # Main daemon entry point
├── cli.py                # Command-line utility (--dry-run, --test-telegram, --once)
├── test_system.py        # Unit & integration test suite
├── .env.example          # Environment variables template
└── README.md             # System documentation
```
