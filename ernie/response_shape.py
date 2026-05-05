"""Response-shape fingerprinting for SmartGEP auth flow.

Phase 2: Fingerprint login HTTP response shape (status, headers, body structure).
Detect when GEP changes auth flow (redirects, error messages, field changes).
"""
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

PROFILES_DIR = Path(__file__).resolve().parent / "profiles"

AUTH_PROBE_URLS = [
    "https://businessnetwork.gep.com/",
    "https://businessnetwork.gep.com/Account/Login",
    "https://idplogin.gep.com/Account/Login",
]

RESPONSE_FIELD_PATTERNS = [
    r'input[^>]*name\s*=\s*["\']?[Uu]sername',
    r'input[^>]*name\s*=\s*["\']?[Pp]assword',
    r'input[^>]*name\s*=\s*["\']?[Ee]mail',
    r'input[^>]*type\s*=\s*["\']?password',
    r'form[^>]*action\s*=',
    r'Login with Password',
    r'Sign In',
    r'error[-\s]?message',
    r'alert[-\s]?(danger|error|warning)',
    r'invalid',
    r'forgot',
    r'captcha',
    r'csrf',
    r'__RequestVerificationToken',
    r'__VIEWSTATE',
]

KEY_HEADERS = [
    "location",
    "set-cookie",
    "content-type",
    "content-length",
    "cache-control",
    "pragma",
    "x-frame-options",
    "strict-transport-security",
]


def fingerprint_redirect_chain(url: str, timeout: int = 15, max_hops: int = 5) -> dict:
    """Follow redirect chain and fingerprint each hop.

    Returns dict with redirect chain metadata and final response shape.
    """
    hops: list[dict] = []
    seen_urls: set[str] = set()
    current_url = url
    final_body = b""
    final_headers: dict[str, str] = {}
    final_status = 0

    for _ in range(max_hops):
        if current_url in seen_urls:
            hops.append({"url": current_url, "status": 0, "error": "redirect_loop", "headers": {}})
            break
        seen_urls.add(current_url)

        try:
            req = Request(current_url, method="GET", headers={"User-Agent": "Ernie/2.0"})
            resp = urlopen(req, timeout=timeout)
            hop_headers = {k.lower(): v for k, v in resp.headers.items() if k.lower() in KEY_HEADERS}
            hops.append({
                "url": current_url,
                "status": resp.status,
                "headers": hop_headers,
            })

            if resp.status in (301, 302, 303, 307, 308):
                next_url = resp.headers.get("Location", "")
                if next_url:
                    current_url = next_url if next_url.startswith("http") else (
                        current_url.rsplit("/", 1)[0] + "/" + next_url.lstrip("/")
                    )
                    final_body = b""
                    continue
                else:
                    hops.append({"url": current_url, "status": resp.status, "error": "redirect_no_location", "headers": {}})
                    break
            else:
                final_body = resp.read()
                final_status = resp.status
                final_headers = hop_headers
                break

        except URLError as e:
            code = getattr(e, "code", 0)
            hops.append({"url": current_url, "status": code, "error": str(e.reason) if hasattr(e, "reason") else str(e)})
            final_status = code
            break
        except Exception as e:
            hops.append({"url": current_url, "status": 0, "error": str(e)})
            break
    else:
        hops.append({"url": current_url, "status": 0, "error": "max_hops_exceeded"})

    body_text = final_body.decode("utf-8", errors="replace") if final_body else ""

    clean_for_hash = re.sub(r'''nonce\s*=\s*['"][^'"]+['"]''', '', body_text)
    clean_for_hash = re.sub(r'value="[A-Za-z0-9+/=]{50,}"', '', clean_for_hash)
    clean_for_hash = re.sub(r'name="__VIEWSTATE".*?/>', '', clean_for_hash)
    clean_for_hash = re.sub(r'name="__EVENTVALIDATION".*?/>', '', clean_for_hash)
    clean_for_hash = re.sub(r'name="__RequestVerificationToken".*?/>', '', clean_for_hash)
    clean_for_hash = re.sub(r'\d{10,}', '', clean_for_hash)

    return {
        "target_url": url,
        "hops": hops,
        "hop_count": len(hops),
        "final_status": final_status,
        "final_url": hops[-1].get("url", url) if hops else url,
        "final_headers": final_headers,
        "body_length": len(final_body),
        "body_markers": extract_body_markers(body_text),
        "body_hash": hashlib.sha256(clean_for_hash.encode()).hexdigest()[:16] if clean_for_hash else "",
        "timestamp": time.time(),
    }


def extract_body_markers(body: str) -> dict:
    """Extract structural markers from HTML body."""
    markers: dict[str, Any] = {}

    markers["has_login_form"] = bool(re.search(r'<form[^>]*action\s*=', body, re.IGNORECASE))
    markers["has_password_field"] = bool(re.search(r'<input[^>]*type\s*=\s*["\']?password', body, re.IGNORECASE))
    markers["has_username_field"] = bool(re.search(r'<input[^>]*(name\s*=\s*["\']?[Uu]sername|id\s*=\s*["\']?[Uu]sername)', body, re.IGNORECASE))
    markers["login_with_password"] = "Login with Password" in body
    markers["sign_in_button"] = bool(re.search(r'Sign\s*[Ii]n', body))
    markers["has_error"] = bool(re.search(r'(error[- ]?message|alert[- ]?(danger|error)|invalid|incorrect)', body, re.IGNORECASE))
    markers["has_captcha"] = bool(re.search(r'(captcha|recaptcha|g-recaptcha)', body, re.IGNORECASE))
    markers["has_csrf_token"] = bool(re.search(r'__RequestVerificationToken|__VIEWSTATE|csrf', body))
    markers["has_forgot_password"] = bool(re.search(r'(forgot|reset)[^ ]*password', body, re.IGNORECASE))

    field_names = re.findall(r'<input[^>]*name\s*=\s*["\']([^"\']+)["\']', body, re.IGNORECASE)
    if field_names:
        markers["field_names"] = sorted(set(field_names[:20]))

    form_actions = re.findall(r'<form[^>]*action\s*=\s*["\']([^"\']+)["\']', body, re.IGNORECASE)
    if form_actions:
        markers["form_actions"] = form_actions[:5]

    return markers


def fingerprint_auth_probe(timeout: int = 30) -> dict:
    """Probe all auth flow URLs and produce a composite fingerprint.

    Returns dict with each URL's response shape.
    """
    results = {}
    for url in AUTH_PROBE_URLS:
        fp = fingerprint_redirect_chain(url, timeout=min(timeout, 15))
        results[url] = fp
    return {
        "probes": results,
        "composite_hash": _composite_hash(results),
        "timestamp": time.time(),
    }


def _composite_hash(probes: dict) -> str:
    """Hash key structural features across all probes for quick comparison."""
    parts: list[str] = []
    for url, fp in sorted(probes.items()):
        parts.append(str(fp.get("hop_count", 0)))
        parts.append(str(fp.get("final_status", 0)))
        markers = fp.get("body_markers", {})
        parts.append(str(markers.get("has_login_form", False)))
        parts.append(str(markers.get("has_password_field", False)))
        parts.append(str(markers.get("has_captcha", False)))
        parts.append(str(markers.get("has_error", False)))
        parts.append(fp.get("body_hash", ""))
        for h in fp.get("hops", []):
            parts.append(str(h.get("status", 0)))
            loc = h.get("headers", {}).get("location", "")
            if loc:
                domain_match = re.search(r'https?://([^/]+)', loc)
                if domain_match:
                    parts.append(domain_match.group(1))
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def load_auth_profile(name: str = "auth_flow") -> dict | None:
    path = PROFILES_DIR / f"{name}_auth_fingerprint.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_auth_profile(name: str, fingerprint: dict):
    path = PROFILES_DIR / f"{name}_auth_fingerprint.json"
    path.write_text(json.dumps(fingerprint, indent=2))
    path.chmod(0o600)


def detect_auth_drift(current: dict) -> list[str]:
    """Compare current auth flow fingerprint against stored baseline.

    Returns list of drift descriptions (empty = no drift).
    """
    profile = load_auth_profile("auth_flow")
    if not profile or not profile.get("fingerprint"):
        save_auth_profile("auth_flow", {"name": "auth_flow", "created": time.time(), "fingerprint": current})
        return []

    baseline = profile["fingerprint"]
    drifts: list[str] = []

    old_hash = baseline.get("composite_hash", "")
    new_hash = current.get("composite_hash", "")
    if old_hash and new_hash and old_hash != new_hash:
        drifts.append("Auth flow composite hash changed (GEP may have modified login flow)")

    old_probes = baseline.get("probes", {})
    new_probes = current.get("probes", {})

    for url in AUTH_PROBE_URLS:
        old_fp = old_probes.get(url, {})
        new_fp = new_probes.get(url, {})
        if not old_fp or not new_fp:
            continue

        old_count = old_fp.get("hop_count", 0)
        new_count = new_fp.get("hop_count", 0)
        if old_count != new_count:
            drifts.append(f"Redirect hop count changed for {url}: {old_count} -> {new_count}")

        old_status = old_fp.get("final_status", 0)
        new_status = new_fp.get("final_status", 0)
        if old_status != new_status:
            drifts.append(f"Final HTTP status changed for {url}: {old_status} -> {new_status}")

        old_markers = old_fp.get("body_markers", {})
        new_markers = new_fp.get("body_markers", {})
        for key in ("has_login_form", "has_password_field", "has_username_field", "has_captcha", "login_with_password", "sign_in_button"):
            if old_markers.get(key) != new_markers.get(key):
                drifts.append(f"Field marker '{key}' changed for {url}: {old_markers.get(key)} -> {new_markers.get(key)}")

        old_fields = set(old_markers.get("field_names", []))
        new_fields = set(new_markers.get("field_names", []))
        if old_fields and new_fields and old_fields != new_fields:
            added = new_fields - old_fields
            removed = old_fields - new_fields
            if added:
                drifts.append(f"New form fields on {url}: {', '.join(sorted(added)[:5])}")
            if removed:
                drifts.append(f"Removed form fields on {url}: {', '.join(sorted(removed)[:5])}")

        old_error = old_markers.get("has_error", False)
        new_error = new_markers.get("has_error", False)
        if old_error != new_error:
            drifts.append(f"Error presence changed for {url}: {old_error} -> {new_error}")

    old_form_actions = set()
    new_form_actions = set()
    for url in AUTH_PROBE_URLS:
        fp = old_probes.get(url, {})
        for action in fp.get("body_markers", {}).get("form_actions", []):
            old_form_actions.add(action)
        fp = new_probes.get(url, {})
        for action in fp.get("body_markers", {}).get("form_actions", []):
            new_form_actions.add(action)
    if old_form_actions and new_form_actions and old_form_actions != new_form_actions:
        added = new_form_actions - old_form_actions
        removed = old_form_actions - new_form_actions
        parts = []
        if added:
            parts.append(f"+{len(added)} actions")
        if removed:
            parts.append(f"-{len(removed)} actions")
        drifts.append(f"Form action URLs changed: {', '.join(parts)}")

    if drifts:
        profile["fingerprint"] = current
        profile["last_drift"] = time.time()
        profile["drift_count"] = profile.get("drift_count", 0) + 1
        save_auth_profile("auth_flow", profile)

    return drifts
