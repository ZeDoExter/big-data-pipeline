"""Scheduler — run batch scoring every 30 min (simulates Azure Function)."""
import subprocess
import time
from datetime import datetime

SCHEDULE_SECONDS = 1800  # 30 minutes


def run_step(name, cmd):
    print(f"[{datetime.now():%H:%M:%S}] {name}...", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:200]}")
        return False
    print(f"  done", flush=True)
    return True


def run_pipeline():
    steps = [
        ("Ingest realtime", ["uv", "run", "python", "src/ingestion/download_ndbc.py", "--realtime-only"]),
        ("Parse", ["uv", "run", "python", "src/ingestion/parse_ndbc.py"]),
        ("Features", ["uv", "run", "python", "src/spark/features.py"]),
        ("Score", ["uv", "run", "python", "src/function/batch_score.py"]),
    ]
    for name, cmd in steps:
        if not run_step(name, cmd):
            print(f"  pipeline stopped at {name}")
            return False
    print(f"[{datetime.now():%H:%M:%S}] pipeline complete", flush=True)
    return True


def main():
    print("Buoy Watch scheduler — runs every 30 min")
    print("Press Ctrl+C to stop\n")
    while True:
        run_pipeline()
        print(f"\nNext run in {SCHEDULE_SECONDS // 60} min...\n", flush=True)
        time.sleep(SCHEDULE_SECONDS)


if __name__ == "__main__":
    main()
