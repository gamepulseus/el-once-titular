import sys
import threading

# Reconfigure stdout/stderr to UTF-8 for Windows console emoji support
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import logging
from scheduler import GamePulseScheduler
from web_server import run_web_server

def main():
    print("==================================================")
    print("      ⚡ GamePulse Web Portal & Auto-Publisher ⚡   ")
    print("      Apple Minimalist Web App: http://localhost:5000")
    print("       Spanish 🇪🇸 & English 🇺🇸 Sports Channels     ")
    print("==================================================")

    # Start Flask Web Server in background thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Start GamePulse Scheduler loop
    scheduler = GamePulseScheduler(dry_run=False)
    
    try:
        scheduler.start_loop()
    except KeyboardInterrupt:
        print("\nStopping GamePulse Auto-Publisher. Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
