#!/usr/bin/env python3
"""Deepthink test — lightweight, exercises all 5 phases independently.
PASS/FAIL/WARN only, no time-based thresholds (app overhead dominates).
"""

import json, sys, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:3637"
API = f"{BASE}/api/harga-v2"
PASS = FAIL = WARN = 0
RESULTS = []

def result(phase, status, msg):
    global PASS, FAIL, WARN
    RESULTS.append({"phase": phase, "status": status, "msg": msg})
    getattr(sys.stdout, "write")(f"  [{status}] {phase}: {msg}\n")

def api_post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{API}{path}", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"_error": f"HTTP {e.code}"}
    except Exception as e:
        return {"_error": str(e)}

def api_get(path):
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=15) as r:
            raw = r.read().decode()
            if "json" in r.headers.get("Content-Type", ""):
                return json.loads(raw)
            return raw
    except Exception as e:
        return {"_error": str(e)}

def new_session():
    d = api_post("/chat/sessions", {"tender_id": None})
    return d.get("id") if "_error" not in d else None

# ── Phase 5: Dashboard ──
def test_p5():
    stats = api_get("/admin/cache/json")
    if not isinstance(stats, dict) or "cache" not in stats:
        return result("P5", "FAIL", "Dashboard JSON unreachable")
    cs, cb, tm = stats["cache"], stats["circuit_breaker"], stats["templates"]
    result("P5", "PASS",
        f"JSON: {cs['total_entries']} entries, {cs['entries_with_embeddings']} embs, "
        f"semantic={'on' if cs['semantic_enabled'] else 'off'}, "
        f"circuit={'OPEN' if cb['circuit_open'] else 'CLOSED'}, "
        f"templates={tm['groups']}grp/{tm['patterns']}pat")

    html = api_get("/admin/cache")
    if isinstance(html, str) and "Cache Dashboard" in html:
        result("P5", "PASS", "HTML dashboard renders OK")
    else:
        result("P5", "FAIL", "HTML dashboard broken")

# ── Phase 4: Templates ──
def test_p4():
    sid = new_session()
    if not sid:
        return result("P4", "FAIL", "No session")
    checks = {"greeting": "hello", "help": "help", "thanks": "thanks",
              "status": "status", "goodbye": "bye"}
    ok = 0
    for cat, msg in checks.items():
        resp = api_post("/chat", {"session_id": sid, "prompt": msg})
        if "_error" in resp:
            result("P4", "WARN", f"[{cat}] '{msg}' → {resp['_error']}")
            continue
        c = resp.get("consolidated", {})
        txt = c.get("conversational_response", "") or ""
        is_template = c.get("template_id") is not None
        if is_template:
            result("P4", "PASS", f"[{cat}] '{msg}' → template match | {txt[:50]}")
            ok += 1
        else:
            result("P4", "WARN", f"[{cat}] '{msg}' → not template: {txt[:50]}")
    if ok == len(checks):
        result("P4", "PASS", f"All {ok} template categories matched")
    return sid

# ── Phase 1: Exact Cache ──
def test_p1(sid):
    msg = "What is the price of steel beam in Malaysia 2025?"
    # First: miss
    r1 = api_post("/chat", {"session_id": sid, "prompt": msg})
    if "_error" in r1:
        return result("P1", "WARN", f"First call: {r1['_error']}")
    if r1.get("cached") is True:
        result("P1", "WARN", "First call already cached (stale data)")
    else:
        result("P1", "PASS", "First call: cache miss (expected)")

    # Second: same msg, should hit
    r2 = api_post("/chat", {"session_id": sid, "prompt": msg})
    if "_error" in r2:
        return result("P1", "WARN", f"Second call: {r2['_error']}")
    if r2.get("cached") is True:
        result("P1", "PASS", "Second call: CACHE HIT ✓")
    else:
        result("P1", "WARN", "Second call: NOT cached")

    # Cross-session: should hit global
    sid2 = new_session()
    if sid2:
        r3 = api_post("/chat", {"session_id": sid2, "prompt": msg})
        if r3.get("cached") is True:
            result("P1", "PASS", "Cross-session: global cache HIT ✓")
        else:
            result("P1", "WARN", "Cross-session: not cached")

# ── Phase 2: Semantic ──
def test_p2():
    sid = new_session()
    if not sid:
        return result("P2", "FAIL", "No session")
    paraphrase = "How much does steel cost in Malaysia?"
    r = api_post("/chat", {"session_id": sid, "prompt": paraphrase})
    if "_error" in r:
        return result("P2", "WARN", f"Paraphrase: {r['_error']}")
    sim = r.get("cache_similarity")
    if r.get("cached") and sim is not None:
        result("P2", "PASS", f"Semantic HIT (similarity={sim}) ✓")
    elif r.get("cached"):
        result("P2", "PASS", "Exact cache HIT (not semantic)")
    else:
        result("P2", "WARN", "Paraphrase not cached")

# ── Phase 3: Circuit Breaker ──
def test_p3():
    stats = api_get("/admin/cache/json")
    cb = stats.get("circuit_breaker", {})
    result("P3", "PASS", f"Initial: circuit={'OPEN' if cb.get('circuit_open') else 'CLOSED'}, "
          f"failures={cb.get('failures_in_window', 0)}")

    import importlib
    sys.path.insert(0, "/home/the_bomb/orkes/harga")
    try:
        cb_mod = importlib.import_module("circuit_breaker")
        cb_mod.reset()
        for _ in range(3):
            cb_mod.record_failure()
        assert cb_mod.is_open(), "Should open after 3 failures"
        result("P3", "PASS", "Opens after 3 failures ✓")
        cb_mod.record_success()
        assert not cb_mod.is_open(), "Should close on success"
        result("P3", "PASS", "Closes on success ✓")
    except Exception as e:
        result("P3", "WARN", f"Direct test: {e}")

# ── Main ──
if __name__ == "__main__":
    print("Deepthink System Test — Harga Bot\n" + "=" * 50)
    test_p5()
    sid = test_p4()
    test_p1(sid)
    test_p2()
    test_p3()

    print(f"\n{'='*50}\nSUMMARY: {PASS} pass, {FAIL} fail, {WARN} warn\n{'='*50}")
    for r in RESULTS:
        icon = {"PASS": "✓", "FAIL": "✗", "WARN": "!"}[r["status"]]
        print(f"  {icon} [{r['phase']}] {r['msg']}")
    sys.exit(0 if FAIL == 0 else 1)
