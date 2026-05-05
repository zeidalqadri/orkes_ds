"""Drift detection for SmartGEP login page and API response shapes.

Compares current page state against stored profiles to detect
silent failures before they cause data loss.
"""
import hashlib
import json
import time
from pathlib import Path

PROFILES_DIR = Path(__file__).resolve().parent / "profiles"


def _profiles_dir() -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR


# ── Page fingerprint ──────────────────────────────────────────────────

LOGIN_SELECTORS = [
    'input[placeholder="Username"]',
    'input[name="Username"]',
    'input[id="Username"]',
    'button:has-text("Login with Password")',
    'input[placeholder="Password"]',
    'input[name="Password"]',
    'input[id="Password"]',
    'input[type="password"]',
    'button[type="submit"]',
    'button:has-text("Sign In")',
    'button:has-text("Login")',
]

LOGIN_HOST_FRAGMENTS = [
    "idplogin.gep.com",
    "smart-idp.gep.com",
    "smart-sts.gep.com",
]

BIZNET_FRAGMENTS = [
    "businessnetwork.gep.com",
]


def _strip_dynamic_tokens(html: str) -> str:
    """Remove tokens that change on every page load (CSRF, VIEWSTATE, nonces, timestamps)."""
    import re
    html = re.sub(r'name="__VIEWSTATE".*?/>', '', html)
    html = re.sub(r'name="__EVENTVALIDATION".*?/>', '', html)
    html = re.sub(r'name="__CSRF".*?/>', '', html)
    html = re.sub(r'name="__RequestVerificationToken".*?/>', '', html)
    html = re.sub(r'''nonce\s*=\s*['"][^'"]+['"]''', '', html)
    html = re.sub(r'value="[A-Za-z0-9+/=]{50,}"', '', html)
    html = re.sub(r'\d{10,}', '', html)
    return html


def fingerprint_page(title: str, url: str, html_snippet: str = "") -> dict:
    """Create a fingerprint dict for a page at a given URL."""
    selector_hashes = {}
    for sel in LOGIN_SELECTORS:
        h = hashlib.sha256(sel.encode()).hexdigest()[:12]
        selector_hashes[sel] = h

    url_domain = _extract_domain(url)
    url_path = url.split("#")[0].split("?")[0]
    clean_html = _strip_dynamic_tokens(html_snippet)

    return {
        "title": title[:200],
        "url_domain": url_domain,
        "url_path": url_path[:200],
        "url_fragment": url.split("#")[1] if "#" in url else "",
        "selector_count": len(LOGIN_SELECTORS),
        "selector_hashes": selector_hashes,
        "login_host_match": any(h in url for h in LOGIN_HOST_FRAGMENTS),
        "biznet_match": any(h in url for h in BIZNET_FRAGMENTS),
        "html_length": len(html_snippet),
        "html_prefix_hash": hashlib.sha256(clean_html[:2000].encode()).hexdigest()[:16] if clean_html else "",
        "timestamp": time.time(),
    }


def _extract_domain(url: str) -> str:
    from urllib.parse import urlparse
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return url[:100]


# ── Profile storage ───────────────────────────────────────────────────


def load_profile(name: str = "login") -> dict | None:
    path = _profiles_dir() / f"{name}_fingerprint.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_profile(name: str, fingerprint: dict):
    path = _profiles_dir() / f"{name}_fingerprint.json"
    path.write_text(json.dumps(fingerprint, indent=2))
    path.chmod(0o600)


def init_profile(name: str = "login") -> dict:
    existing = load_profile(name)
    if existing:
        return existing
    blank = {
        "name": name,
        "created": time.time(),
        "fingerprint": None,
    }
    save_profile(name, blank)
    return blank


# ── Drift detection ───────────────────────────────────────────────────


def detect_drift(name: str, current: dict) -> list[str]:
    """Compare current fingerprint against stored profile.

    Returns list of drift descriptions (empty = no drift).
    """
    profile = load_profile(name)
    if not profile or not profile.get("fingerprint"):
        save_profile(name, {"name": name, "created": time.time(), "fingerprint": current})
        return []

    baseline = profile["fingerprint"]
    drifts = []

    if baseline.get("login_host_match") != current.get("login_host_match"):
        drifts.append(f"login_host_match changed: {baseline.get('login_host_match')} -> {current.get('login_host_match')}")

    if baseline.get("biznet_match") != current.get("biznet_match"):
        drifts.append(f"biznet_match changed: {baseline.get('biznet_match')} -> {current.get('biznet_match')}")

    if baseline.get("url_domain") != current.get("url_domain"):
        drifts.append(f"domain changed: {baseline.get('url_domain')} -> {current.get('url_domain')}")

    bh = baseline.get("html_prefix_hash", "")
    ch = current.get("html_prefix_hash", "")
    if bh and ch and bh != ch:
        drifts.append("HTML prefix hash mismatch (page structure may have changed)")

    if drifts:
        save_profile(name, {"name": name, "created": profile.get("created", time.time()), "fingerprint": current, "last_drift": time.time(), "drift_count": profile.get("drift_count", 0) + 1})

    return drifts


# ── API response shape fingerprint (Phase 2 stub) ─────────────────────


def fingerprint_json_response(data: dict | list) -> dict:
    """Create a shape fingerprint from a JSON API response."""
    def _shape(obj, depth=0):
        if depth > 10:
            return "..."
        if isinstance(obj, dict):
            return {k: _shape(v, depth + 1) for k, v in obj.items()}
        elif isinstance(obj, list):
            if obj:
                inner = _shape(obj[0], depth + 1)
                return f"list<{json.dumps(inner)}>"
            return "list<unknown>"
        else:
            return type(obj).__name__
    return {
        "shape": _shape(data),
        "top_keys": list(data.keys()) if isinstance(data, dict) else [],
        "timestamp": time.time(),
    }
