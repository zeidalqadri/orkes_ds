"""Restore context markdown files from a timestamped snapshot.

Usage:
    python scripts/restore_state.py list              # list available snapshots
    python scripts/restore_state.py <timestamp>        # restore from snapshot
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTEXT = ROOT / "context"
BACKUPS = CONTEXT / "backups"


def list_snapshots():
    snapshots = sorted(BACKUPS.iterdir()) if BACKUPS.exists() else []
    if not snapshots:
        print("No snapshots found.")
        return
    for s in snapshots:
        if s.is_dir():
            meta = s / ".meta"
            created = meta.read_text().strip() if meta.exists() else "unknown"
            files = [f.name for f in s.iterdir() if f.is_file() and f.name != ".meta"]
            print(f"  {s.name}  ({', '.join(files)})  [{created}]")


def restore(timestamp: str):
    snap = BACKUPS / timestamp
    if not snap.exists() or not snap.is_dir():
        print(f"Snapshot not found: {timestamp}", file=sys.stderr)
        print("Available:", file=sys.stderr)
        list_snapshots()
        return False

    count = 0
    for f in snap.iterdir():
        if f.is_file() and f.name != ".meta":
            dest = CONTEXT / f.name
            shutil.copy2(f, dest)
            count += 1

    print(f"Restored {count} file(s) from {timestamp}.")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/restore_state.py list")
        print("  python scripts/restore_state.py <timestamp>")
        return

    cmd = sys.argv[1]
    if cmd == "list":
        list_snapshots()
    else:
        restore(cmd)


if __name__ == "__main__":
    main()
