#!/usr/bin/env python3
"""Clear all existing tender data to start fresh with source-reference IDs.

Drops all rows from tenders, wizard_sessions, pricing_versions tables
and removes all tender directories from disk.
"""

import shutil
import sqlite3
import sys
from pathlib import Path

# Resolve paths
YP_DIR = Path("/home/the_bomb/orkes/yellowpages")
TENDERS_DIR = YP_DIR / "tenders"

if not TENDERS_DIR.exists():
    print(f"TENDERS_DIR not found: {TENDERS_DIR}", file=sys.stderr)
    sys.exit(1)

DB_PATH = TENDERS_DIR / "tenders.db"

def count_tables(conn):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    counts = {}
    for row in cur.fetchall():
        name = row[0]
        cnt = conn.execute(f"SELECT COUNT(*) FROM \"{name}\"").fetchone()[0]
        counts[name] = cnt
    return counts

def main():
    print(f"Database: {DB_PATH}")
    print(f"Tenders dir: {TENDERS_DIR}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = OFF")

    before = count_tables(conn)
    print("\nBefore clearing:")
    for t, c in before.items():
        print(f"  {t}: {c} rows")

    total_tenders = before.get("tenders", 0)
    total_sessions = before.get("wizard_sessions", 0)
    total_pricing = before.get("pricing_versions", 0)

    # Clear tables
    conn.execute("DELETE FROM pricing_versions")
    conn.execute("DELETE FROM wizard_sessions")
    conn.execute("DELETE FROM tenders")
    conn.commit()

    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()

    # Remove tender directories
    tender_dirs = sorted([d for d in TENDERS_DIR.iterdir() if d.is_dir()])
    rm_count = 0
    for d in tender_dirs:
        if d.name == "__pycache__":
            continue
        shutil.rmtree(d, ignore_errors=True)
        rm_count += 1
    print(f"\nRemoved {rm_count} tender directories from disk")
    print(f"Cleared {total_tenders} tenders, {total_sessions} wizard sessions, {total_pricing} pricing versions")

    print("\nDone. System ready for fresh imports with source-reference IDs.")


if __name__ == "__main__":
    main()
