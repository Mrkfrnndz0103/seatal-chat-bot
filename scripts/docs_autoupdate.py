from __future__ import annotations

import argparse
import time
from pathlib import Path

from sync_docs import sync_files

WATCH_TARGETS = [
    Path("app/seatalk/event_types.py"),
    Path("app/seatalk/client.py"),
    Path("app/seatalk/auth.py"),
]


def _snapshot(root: Path) -> dict[Path, int]:
    state: dict[Path, int] = {}
    for relative in WATCH_TARGETS:
        path = root / relative
        if not path.exists():
            continue
        state[relative] = path.stat().st_mtime_ns
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-update README and implementation docs")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    sync_files(root)
    print("Initial doc sync complete. Watching for source changes...")

    previous = _snapshot(root)
    try:
        while True:
            time.sleep(args.interval)
            current = _snapshot(root)
            if current != previous:
                sync_files(root)
                print("Detected source changes. Docs updated.")
                previous = current
    except KeyboardInterrupt:
        print("Stopped doc auto-update watcher.")


if __name__ == "__main__":
    main()
