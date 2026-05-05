"""Backup context markdown files with timestamped snapshots.

Usage:
    python scripts/backup_state.py          # create snapshot
    python scripts/backup_state.py --prune   # remove snapshots older than 7 days

Retention: 7 days of snapshots.
"""
import argparse
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTEXT = ROOT / "context"
BACKUPS = CONTEXT / "backups"

FILES = ["STATE.md", "GOAL.md", "INBOX.md", "experts.json", "bot.json"]
RETENTION_DAYS = 7


def backup():
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    snap = BACKUPS / timestamp
    snap.mkdir(parents=True, exist_ok=True)
    count = 0
    for name in FILES:
        src = CONTEXT / name
        if src.exists():
            shutil.copy2(src, snap / name)
            count += 1
    (snap / ".meta").write_text(
        f"created_at={timestamp}\nsource={CONTEXT}\n"
    )
    return count, timestamp


def prune():
    cutoff = time.time() - RETENTION_DAYS * 86400
    removed = 0
    for entry in sorted(BACKUPS.iterdir()):
        if not entry.is_dir():
            continue
        try:
            ts = entry.name
            t = time.mktime(time.strptime(ts, "%Y%m%d-%H%M%S"))
            if t < cutoff:
                shutil.rmtree(entry)
                removed += 1
        except (ValueError, OSError):
            continue
    return removed


def main():
    parser = argparse.ArgumentParser(description="Backup context state files")
    parser.add_argument("--prune", action="store_true", help="Remove old snapshots")
    args = parser.parse_args()

    if args.prune:
        n = prune()
        print(f"Pruned {n} old snapshot(s).")
        return

    count, ts = backup()
    print(f"Backup {ts}: {count} file(s) saved to context/backups/{ts}/")


if __name__ == "__main__":
    main()
