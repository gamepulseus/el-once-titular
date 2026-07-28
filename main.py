import sys
import logging
from scheduler import GamePulseScheduler

# Reconfigure stdout/stderr to UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    print("==================================================")
    print("      ⚡ GamePulse 24/7 Sports Auto-Publisher ⚡   ")
    print("       Telegram @GamePulseUS & Twitter @GamePulseUS")
    print("==================================================")

    # Start GamePulse Scheduler loop
    scheduler = GamePulseScheduler(dry_run=False)
    
    try:
        scheduler.start_loop()
    except KeyboardInterrupt:
        print("\nStopping GamePulse Auto-Publisher. Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
