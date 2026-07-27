import argparse
import sys
import io

# Reconfigure stdout/stderr to UTF-8 for Windows console emoji support
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from scheduler import GamePulseScheduler
from telegram_publisher import TelegramPublisher

def main():
    parser = argparse.ArgumentParser(description="GamePulse CLI Tool")
    parser.add_argument("--dry-run", action="store_true", help="Fetch live ESPN data and print formatted posts in Spanish & English without publishing to Telegram.")
    parser.add_argument("--once", action="store_true", help="Run a single cycle (News, Scoreboard, Standings) and exit.")
    parser.add_argument("--test-telegram", action="store_true", help="Send a test ping message to the configured Spanish and English Telegram channels.")
    
    args = parser.parse_args()

    if args.test_telegram:
        print("Sending test messages to Telegram channels...")
        pub = TelegramPublisher()
        if not pub.is_configured():
            print("⚠️ WARNING: Telegram bot token is not configured in .env!")
        res_es, res_en = pub.publish_bilingual(
            msg_es="🧪 <b>GamePulse Test</b>: El canal en Español está configurado correctamente.",
            msg_en="🧪 <b>GamePulse Test</b>: The English channel is successfully configured."
        )
        print(f"Spanish Channel Result: {'SUCCESS ✅' if res_es else 'FAILED ❌'}")
        print(f"English Channel Result: {'SUCCESS ✅' if res_en else 'FAILED ❌'}")
        sys.exit(0)

    dry_run = args.dry_run
    scheduler = GamePulseScheduler(dry_run=dry_run)

    if args.once or dry_run:
        scheduler.run_once()
    else:
        scheduler.start_loop()

if __name__ == "__main__":
    main()
