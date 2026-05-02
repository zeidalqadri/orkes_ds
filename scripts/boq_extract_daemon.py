#!/usr/bin/env python3
"""BoQ extraction via the permauth daemon's /boq-extract endpoint.

Usage:
    python scripts/boq_extract_daemon.py              # batch all 6 events
    python scripts/boq_extract_daemon.py --event RFP-000000178771  # single
    python scripts/boq_extract_daemon.py --dry-run     # show what would run
"""
import json
import sys
import time
from argparse import ArgumentParser
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

DAEMON_URL = "http://127.0.0.1:9876"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "pricesheet_extract"
CHECKPOINT_PATH = OUTPUT_DIR / "boq_daemon_checkpoint.json"
EVENT_ID_MAP_PATH = OUTPUT_DIR / "event_id_map.json"

EVENTS = [
    "RFP-000000178771", "RFP-000000178432", "RFP-000000178387",
    "RFP-000000178027", "RFP-000000177523", "RFP-000000176710",
]


def load_event_map() -> dict:
    if EVENT_ID_MAP_PATH.exists():
        return json.loads(EVENT_ID_MAP_PATH.read_text())
    return {}


def load_checkpoint() -> set:
    if CHECKPOINT_PATH.exists():
        return set(json.loads(CHECKPOINT_PATH.read_text()))
    return set()


def save_checkpoint(completed: set):
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(json.dumps(sorted(completed)))


def check_daemon_health() -> bool:
    try:
        resp = urlopen(f"{DAEMON_URL}/health", timeout=5)
        data = json.loads(resp.read().decode())
        if data.get("alive") and data.get("cookies_count", 0) > 0:
            print(f"[init] Daemon OK: alive={data['alive']} cookies={data['cookies_count']}")
            return True
        print(f"[init] Daemon not ready: alive={data.get('alive')} cookies={data.get('cookies_count', 0)}")
        return False
    except Exception as e:
        print(f"[init] Daemon unreachable: {e}")
        return False


def extract_boq(event_number: str, event_map: dict, timeout: int = 120) -> dict | None:
    entry = event_map.get(event_number, {})
    payload = {
        "event_number": event_number,
        "event_id": entry.get("event_id", ""),
        "doc_url": entry.get("doc_url", ""),
        "oloc": entry.get("oloc", 219),
    }
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{DAEMON_URL}/boq-extract",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print(f"[boq] {event_number}: extracting...")
    start = time.time()
    try:
        resp = urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode())
        elapsed = time.time() - start
        items_count = data.get("items_count", 0)
        status = data.get("status", "?")
        error = data.get("error", "")
        print(f"[boq] {event_number}: {items_count} items in {elapsed:.0f}s (status={status})")
        if error:
            print(f"[boq] {event_number}: ERROR: {error}")
        return data
    except Exception as e:
        elapsed = time.time() - start
        print(f"[boq] {event_number}: FAILED after {elapsed:.0f}s: {e}")
        return None


def save_output(event_number: str, data: dict):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = OUTPUT_DIR / f"boq_{event_number}.json"
    with open(fname, "w") as f:
        json.dump(data, f, ensure_ascii=False, default=str, indent=2)
    print(f"[save] {event_number} → {fname}")


def main():
    parser = ArgumentParser(description="BoQ extraction via permauth daemon")
    parser.add_argument("--event", help="Single event number to extract")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per event (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run")
    parser.add_argument("--force", action="store_true", help="Re-extract already completed events")
    args = parser.parse_args()

    print(f"[{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}] BoQ Daemon Extractor")
    print()

    if not check_daemon_health():
        print("Daemon not ready — aborting")
        sys.exit(1)

    event_map = load_event_map()
    if not event_map:
        print("No event_id_map.json found — aborting")
        sys.exit(1)

    targets = [args.event] if args.event else EVENTS
    completed = set() if args.force else load_checkpoint()

    if args.dry_run:
        for evt in targets:
            status = "DONE" if evt in completed else "PENDING"
            entry = event_map.get(evt, {})
            print(f"  {evt}: {status} (id={entry.get('event_id','?')})")
        return

    failed = []
    success = []
    for evt in targets:
        if evt in completed:
            print(f"[skip] {evt}: already completed")
            continue
        result = extract_boq(evt, event_map, timeout=args.timeout)
        if result and result.get("items_count", 0) > 0:
            save_output(evt, result)
            completed.add(evt)
            save_checkpoint(completed)
            success.append(evt)
        else:
            failed.append(evt)

    print()
    print(f"Summary: {len(success)} succeeded, {len(failed)} failed, {len(completed) - len(success)} previously done")
    if failed:
        print(f"Failed: {failed}")


if __name__ == "__main__":
    main()
