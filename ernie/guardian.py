#!/usr/bin/env python3
"""Ernie — Guardian agent for SmartGEP scraping health.

Health probes the Cookie Monster (permauth daemon) every 5 minutes,
detects drift in login page structure, and alerts on silent failures.

Designed to be run as a pm2 daemon alongside permauth.

Phase 1:
  - Health probe → /health on Cookie Monster (localhost:9876)
  - Drift detection on login page
  - Telegram alerting

Usage:
  python -m ernie.guardian [--interval 300] [--cookie-monster-port 9876]
"""
import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ernie.alert import send_alert
from ernie.drift_detect import (
    detect_drift,
    fingerprint_page,
    init_profile,
)
from ernie.response_shape import (
    detect_auth_drift,
    fingerprint_auth_probe,
)
from ernie.theming import alert_line, status_line

GUARDIAN_STATE_FILE = Path(__file__).resolve().parent / "state.json"
DEFAULT_PORT = int(os.environ.get("COOKIE_MONSTER_PORT", "9876"))
DEFAULT_INTERVAL = int(os.environ.get("ERNIE_INTERVAL", "300"))


def _load_state() -> dict:
    if GUARDIAN_STATE_FILE.exists():
        try:
            return json.loads(GUARDIAN_STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"down_since": None, "drift_since": None, "total_checks": 0, "total_alerts": 0}


def _save_state(state: dict):
    GUARDIAN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    GUARDIAN_STATE_FILE.write_text(json.dumps(state, indent=2))
    GUARDIAN_STATE_FILE.chmod(0o600)


# ── Health probe ──────────────────────────────────────────────────────


def probe_cookie_monster(port: int = 9876) -> dict:
    """Probe the Cookie Monster health endpoint.

    Returns dict with at least {"alive": bool}.
    On success, includes all fields from Cookie Monster's /health.
    """
    result = {"alive": False, "error": ""}
    try:
        req = Request(f"http://127.0.0.1:{port}/health", method="GET")
        resp = urlopen(req, timeout=10)
        body = json.loads(resp.read().decode())
        result["alive"] = True
        result.update(body)
    except URLError as e:
        result["error"] = str(e.reason) if hasattr(e, "reason") else str(e)
    except json.JSONDecodeError as e:
        result["alive"] = True
        result["error"] = f"bad json: {e}"
    except Exception as e:
        result["error"] = str(e)
    return result


def probe_url(url: str, timeout: int = 15) -> dict:
    """Probe a URL and return status + snippet for fingerprinting.

    Returns dict with at least {"reachable": bool, "status": int, "snippet": str}.
    """
    result = {"reachable": False, "status": 0, "snippet": "", "url": url}
    try:
        req = Request(url, method="GET", headers={"User-Agent": "Ernie/1.0"})
        resp = urlopen(req, timeout=timeout)
        data = resp.read()
        status = resp.status
        result["reachable"] = True
        result["status"] = status
        result["snippet"] = data.decode("utf-8", errors="replace")[:2000]
    except URLError as e:
        if hasattr(e, "code") and e.code:
            result["status"] = e.code
        result["error"] = str(e.reason) if hasattr(e, "reason") else str(e)
    except Exception as e:
        result["error"] = str(e)
    return result


# ── Full check chain ──────────────────────────────────────────────────


def run_check(port: int = 9876) -> dict:
    """Run one full health check cycle.

    Returns result dict for state tracking.
    """
    ts = datetime.now(UTC).isoformat()
    result = {"timestamp": ts, "ok": True, "alerts": []}

    # 1. Probe Cookie Monster
    cm = probe_cookie_monster(port)
    result["cookie_monster"] = cm
    if not cm["alive"]:
        result["ok"] = False
        result["alerts"].append(f"Cookie Monster down: {cm.get('error', 'no response')}")

    # 2. Probe BizNet login page
    bn = probe_url("https://businessnetwork.gep.com/")
    result["biznet"] = bn
    if not bn["reachable"]:
        result["alerts"].append(f"BizNet unreachable: {bn.get('error', 'no response')}")

    # 3. Fingerprint and drift-detect (page structure)
    fp = fingerprint_page(
        title="BizNet",
        url=bn.get("url", ""),
        html_snippet=bn.get("snippet", ""),
    )
    result["fingerprint"] = fp

    drifts = detect_drift("login", fp)
    result["drifts"] = drifts
    if drifts:
        result["ok"] = False
        result["alerts"].extend(f"Drift: {d}" for d in drifts)

    # 4. Auth flow response-shape fingerprinting (Phase 2)
    auth_fp = fingerprint_auth_probe(timeout=20)
    result["auth_fingerprint"] = auth_fp
    auth_drifts = detect_auth_drift(auth_fp)
    result["auth_drifts"] = auth_drifts
    if auth_drifts:
        result["ok"] = False
        result["alerts"].extend(f"Auth flow: {d}" for d in auth_drifts)

    return result


# ── Main loop ─────────────────────────────────────────────────────────


def patrol_section(label: str, ok: bool, detail: str = "") -> str:
    """Format a structured patrol section line."""
    icon = "\u2705" if ok else "\u274c"  # ✅ or ❌
    tag = "OK" if ok else "FAIL"
    d = f" \u2014 {detail}" if detail else ""
    return f"  [{tag}] {icon} {label}{d}"


SEP = "\u2550" * 60  # ════════════════════════════════════════════════════
RECOVERY_MARKER = "\u25b0\u25b0\u25b0 RECOVERY \u25b0\u25b0\u25b0"
ALERT_MARKER = "\u25b0\u25b0\u25b0 ALERT \u25b0\u25b0\u25b0"


def main_loop(interval: int = DEFAULT_INTERVAL, port: int = DEFAULT_PORT):
    state = _load_state()
    init_profile("login")
    was_ok = True

    while True:
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{SEP}", flush=True)
        print(f"  [{ts}] Ernie \U0001f43b Patrol Begin", flush=True)
        print(f"{SEP}", flush=True)

        result = run_check(port)
        patrol = state.get("total_checks", 0) + 1
        state["total_checks"] = patrol
        state["last_check"] = result["timestamp"]

        cm = result.get("cookie_monster", {})
        cm_alive = cm.get("alive", False)
        cm_cookies = cm.get("cookies_count", 0) or 0
        drifts = result.get("drifts", []) + result.get("auth_drifts", [])
        drift_count = len(drifts)
        ernie_ok = result.get("ok", True)

        # ── Section 1: Cookie Monster health ──
        cm_detail = f"{cm_cookies} cookies" if cm_cookies else ""
        if not cm_alive:
            cm_detail = cm.get("error", "no response")
        print(patrol_section("Cookie Monster \U0001f36a health", cm_alive, cm_detail), flush=True)

        # ── Section 2: BizNet reachability ──
        bn = result.get("biznet", {})
        bn_ok = bn.get("reachable", False)
        bn_detail = f"HTTP {bn.get('status', 0)}" if bn_ok else bn.get("error", "no response")
        print(patrol_section("BizNet reachability", bn_ok, bn_detail), flush=True)

        # ── Section 3: Page drift ──
        page_drifts = result.get("drifts", [])
        page_ok = len(page_drifts) == 0
        page_detail = f"{len(page_drifts)} drift(s)" if page_drifts else "no change"
        print(patrol_section("Page drift", page_ok, page_detail), flush=True)
        for d in page_drifts:
            print(f"    \U0001f50d {d}", flush=True)

        # ── Section 4: Auth flow drift ──
        auth_drifts = result.get("auth_drifts", [])
        auth_ok = len(auth_drifts) == 0
        auth_detail = f"{len(auth_drifts)} drift(s)" if auth_drifts else "no change"
        print(patrol_section("Auth flow drift", auth_ok, auth_detail), flush=True)
        for d in auth_drifts:
            print(f"    \U0001f50d {d}", flush=True)

        cm_degraded = bool(page_drifts or auth_drifts) and cm_alive
        print(status_line(patrol, cm_alive, cm_degraded, ernie_ok, drift_count, cm_cookies), flush=True)

        # ── Alert/Recovery transitions ──
        if ernie_ok:
            state["down_since"] = None
            state["drift_since"] = None
            if not was_ok:
                print(f"\n{SEP}", flush=True)
                print(f"  {RECOVERY_MARKER}: All checks passed", flush=True)
                print(alert_line("All checks passed \u2014 recovered", is_recovery=True), flush=True)
                print(f"{SEP}\n", flush=True)
                send_alert("All checks passed \u2014 recovered")
            was_ok = True
        else:
            for alert_msg in result["alerts"]:
                should_alert = False
                alert_key = None

                if "Cookie Monster down" in alert_msg:
                    alert_key = "down_since"
                elif "Drift" in alert_msg or "Auth flow" in alert_msg:
                    alert_key = "drift_since"

                if alert_key and state.get(alert_key) is None:
                    state[alert_key] = result["timestamp"]
                    should_alert = True

                if should_alert:
                    print(f"\n{SEP}", flush=True)
                    print(f"  {ALERT_MARKER}: {alert_msg}", flush=True)
                    themed = alert_line(alert_msg)
                    print(themed, flush=True)
                    print(f"{SEP}\n", flush=True)
                    send_alert(alert_msg)
                    state["total_alerts"] = state.get("total_alerts", 0) + 1

            was_ok = False

        # ── Footer ──
        print(f"{SEP}", flush=True)
        print(f"  [{datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Patrol #{patrol} complete"
              f" {'\U0001f604 all good' if ernie_ok else '\U0001f61e issues detected'}", flush=True)
        print(f"{SEP}\n", flush=True)

        _save_state(state)
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Ernie — SmartGEP scraping guardian")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Check interval in seconds")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Cookie Monster HTTP port")
    args = parser.parse_args()

    try:
        main_loop(interval=args.interval, port=args.port)
    except KeyboardInterrupt:
        print("Ernie stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
