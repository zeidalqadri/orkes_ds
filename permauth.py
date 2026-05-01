#!/usr/bin/env python3
"""
permauth — Persistent Playwright Auth Daemon ("Cookie Monster")

Keeps a long-lived headless Chromium pinned to a SmartGEP SPA event detail,
extracts SPA runtime state (netsessionid, requestverificationtoken, oloc, cookies)
and serves them via HTTP API.

The core insight: SmartGEP's /data/ tier needs SPA heap state (netsessionid,
requestverificationtoken, oloc) — things no cookie jar provides. A persistent
browser daemon amortises the 30-60s login cost to zero for scrapers.

API:
  GET /health   → {alive, uptime, account, page_url, tokens_valid, last_refresh}
  GET /tokens   → {netsessionid, requestverificationtoken, oloc, cookies[], account}
  POST /reload  → force page refresh

Usage:
  python permauth.py [--account consurv] [--port 9876]
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

SMARTGEP_ENGINE = Path("/home/the_bomb/orkes/yellowpages/scrapers/smartgep_engine_v2")
if str(SMARTGEP_ENGINE) not in sys.path:
    sys.path.insert(0, str(SMARTGEP_ENGINE))

class PermauthEmojiFormatter(logging.Formatter):
    """Adds 🍪 mood emoji based on log level."""
    MOODS = {
        logging.DEBUG: "\U0001f36a",       # 🍪
        logging.INFO: "\U0001f60a\U0001f36a",  # 😊🍪
        logging.WARNING: "\U0001f61f\U0001f36a", # 😟🍪
        logging.ERROR: "\U0001f480\U0001f36a",   # 💀🍪
        logging.CRITICAL: "\U0001f480\U0001f36a",# 💀🍪
    }

    def format(self, record):
        emoji = self.MOODS.get(record.levelno, "\U0001f36a")
        original = record.msg
        record.msg = f"{emoji} {record.msg}"
        result = super().format(record)
        record.msg = original
        return result


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(PermauthEmojiFormatter(
    fmt="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
logging.basicConfig(level=logging.INFO, handlers=[_handler])
logger = logging.getLogger("permauth")

ACCOUNTS_PATH = Path("/home/the_bomb/orkes/yellowpages/scrapers/smartgep_accounts.json")
DATA_DIR = Path("/home/the_bomb/orkes/yellowpages/scrapers/data")
REFRESH_INTERVAL = 600
RELOAD_TIMEOUT = 45000
SETTLE_TIME = 12000


SEP = "\u2550" * 60
OK_TAG = "[OK] \u2705"
FAIL_TAG = "[FAIL] \u274c"
WARN_TAG = "[WARN] \u26a0\ufe0f"

def patrol_section(label: str, ok: bool, detail: str = "") -> str:
    icon = "\u2705" if ok else "\u274c"
    tag = "OK" if ok else "FAIL"
    d = f" \u2014 {detail}" if detail else ""
    return f"  [{tag}] {icon} {label}{d}"


class PermauthDaemon:
    def __init__(self, account_id: str, port: int = 9876):
        self.account_id = account_id
        self.port = port
        self.account: Optional[Dict] = self._load_account(account_id)
        self.cookies_path = DATA_DIR / f"smartgep_cookies_{account_id}.json"

        self.browser = None
        self.context = None
        self.page = None
        self._pw = None

        self._tokens: Dict[str, Any] = {"cookies": []}
        self._last_refresh: float = 0
        self._start_time: float = 0
        self._current_url: str = "https://businessnetwork.gep.com/BusinessNetwork/Landing/v2#/bn-landing"

    @staticmethod
    def _load_account(account_id: str) -> Dict:
        data = json.loads(ACCOUNTS_PATH.read_text())
        for a in data.get("accounts", []):
            if a["id"] == account_id:
                return a
        raise ValueError(f"Account '{account_id}' not found")

    async def start(self):
        self._start_time = time.monotonic()
        print(f"\n{SEP}", flush=True)
        print(f"  Cookie Monster \U0001f36a Starting — account={self.account_id} port={self.port}", flush=True)
        print(f"{SEP}", flush=True)
        server = await asyncio.start_server(self._handle_http, "127.0.0.1", self.port)
        print(patrol_section("HTTP API", True, f"http://127.0.0.1:{self.port}"), flush=True)
        print(f"{SEP}\n", flush=True)
        asyncio.create_task(self._init_browser())
        asyncio.create_task(self._refresh_loop())
        async with server:
            await server.serve_forever()

    async def _init_browser(self):
        from playwright.async_api import async_playwright

        print(f"\n{SEP}", flush=True)
        print(f"  \U0001f36a Cookie Monster Browser Init — account={self.account_id}", flush=True)
        print(f"{SEP}", flush=True)

        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        print(patrol_section("Chromium launched", True), flush=True)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        self.page = await self.context.new_page()

        # Apply stealth to evade headless detection
        try:
            from playwright_stealth import Stealth
            await Stealth().apply_stealth_async(self.page)
            logger.info("playwright-stealth applied to browser page")
        except ImportError:
            logger.warning("playwright-stealth not installed — headless detection risk")
        except Exception as e:
            logger.warning("stealth_async failed (non-fatal): %s", e)

        # Step 1: Navigate to idplogin.gep.com directly (mirrors scraper's login flow).
        # The scraper stays on businessnetwork.gep.com after login — NOT smart.gep.com.
        # Direct page.goto() to smart.gep.com breaks the SSO session context.
        # We'll stay on BizNet and serve cookies for HTTP-based API access.
        login_url = "https://idplogin.gep.com"
        print(patrol_section("Login", False, f"navigating to {login_url}"), flush=True)

        nav_ok = False
        for attempt in range(3):
            try:
                await self.page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
                await self.page.wait_for_timeout(8000)
                self._current_url = self.page.url
                logger.info("Login nav (attempt %d): %s", attempt + 1, self._current_url[:120])
                if "chrome-error" not in self._current_url:
                    nav_ok = True
                    break
            except Exception as e:
                logger.warning("Login nav attempt %d: %s", attempt + 1, e)
                await self.page.wait_for_timeout(5000)

        url_lower = self.page.url.lower() if self.page else ""

        if "businessnetwork.gep.com" in url_lower and "login" not in url_lower:
            print(patrol_section("Session valid", True, "already on BizNet"), flush=True)
        elif any(h in url_lower for h in ["idplogin", "smart-sts", "authenticate", "login"]):
            print(patrol_section("SSO page", True, "performing login"), flush=True)
            login_ok = await self._ensure_login()
            if login_ok:
                cook_count = len(self._tokens.get("cookies", []))
                print(patrol_section("Login", True, f"cookies={cook_count}"), flush=True)
            else:
                print(patrol_section("Login", False, "failed"), flush=True)
                logger.warning("Login failed")
        elif "chrome-error" in url_lower:
            print(patrol_section("Navigation", False, "chrome-error — loading cached cookies"), flush=True)
            try:
                cached = self._load_cookies()
                if cached:
                    safe = []
                    for c in cached:
                        domain = (c.get("domain") or "").lstrip(".")
                        if domain:
                            safe.append({
                                "name": c["name"], "value": c["value"],
                                "domain": domain, "path": c.get("path", "/"),
                                "secure": c.get("secure", True),
                                "httpOnly": c.get("httpOnly", False),
                            })
                    if safe:
                        await self.context.add_cookies(safe)
                        logger.info("Fallback: injected %d cached cookies", len(safe))
                # Navigate to biznet — use cached cookies for session
                await self.page.goto(
                    "https://businessnetwork.gep.com/",
                    wait_until="domcontentloaded", timeout=45000,
                )
                await self.page.wait_for_timeout(5000)
                self._current_url = self.page.url
                logger.info("Recovered from chrome-error to: %s", self._current_url[:80])
            except Exception:
                pass

        await self._save_cookies()
        await self._extract_tokens()

        nsid = self._tokens.get("netsessionid") or "NONE"
        cook_count = len(self._tokens.get("cookies", []))
        print(patrol_section("Browser initialized", cook_count > 0, f"nsid={nsid[:12]} cookies={cook_count}"), flush=True)
        print(f"{SEP}\n", flush=True)
        logger.info(
            "Browser initialized — URL: %s nsid=%s cookies=%d",
            (self.page.url[:80] if self.page else "none"),
            nsid[:12],
            cook_count,
        )

    def _load_cookies(self) -> List[Dict]:
        paths = [self.cookies_path]
        # Also check for the fresh cookies from SmartGEPAuth login test
        alt = DATA_DIR / f"smartgep_cookies_{self.account_id}.json"
        if alt != self.cookies_path and alt.exists():
            paths.append(alt)
        for p in paths:
            if p and p.exists():
                try:
                    data = json.loads(p.read_text())
                    cookies = data.get("cookies", [])
                    if cookies:
                        logger.info("Loaded %d cookies from %s", len(cookies), p.name)
                        return cookies
                except Exception as e:
                    logger.warning("Failed to load cookies from %s: %s", p.name, e)
        return []

    async def _save_cookies(self):
        if not self.context or not self.cookies_path:
            return
        try:
            raw = await self.context.cookies()
            cookies = []
            for c in raw:
                domain = c.get("domain", "") or ""
                entry = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": domain.lstrip(".") if domain else "",
                    "path": c.get("path", "/"),
                    "secure": c.get("secure", True),
                    "httpOnly": c.get("httpOnly", False),
                }
                if domain:
                    entry["url"] = f"https://{domain.lstrip('.')}{c.get('path', '/')}"
                cookies.append(entry)
            self.cookies_path.parent.mkdir(parents=True, exist_ok=True)
            self.cookies_path.write_text(
                json.dumps({"cookies": cookies, "saved_at": datetime.now(timezone.utc).isoformat()}, indent=2)
            )
            self.cookies_path.chmod(0o600)
        except Exception as e:
            logger.warning("Failed to save cookies: %s", e)

    async def _ensure_login(self) -> bool:
        """Perform interactive login through SSO chain on idplogin.gep.com.
        After login, SSO chain redirects to businessnetwork.gep.com (BizNet).
        Stays on BizNet — does NOT navigate to smart.gep.com (breaks session).
        Returns True if authenticated with cookies (>10)."""
        if not self.page:
            return False

        current_url = self.page.url.lower()
        on_biznet = "businessnetwork.gep.com" in current_url and "login" not in current_url

        # Already on BizNet with cookies — good enough
        if on_biznet:
            if len(self._tokens.get("cookies", [])) > 10:
                return True
            try:
                await self.page.reload(wait_until="domcontentloaded", timeout=30000)
                await self.page.wait_for_timeout(5000)
            except Exception:
                pass
            self._current_url = self.page.url
            await self._extract_tokens()
            if len(self._tokens.get("cookies", [])) > 10:
                await self._save_cookies()
                return True

        print(f"\n{SEP}", flush=True)
        print(f"  \U0001f36a Cookie Monster Interactive Login \u2014 account={self.account_id}", flush=True)
        print(f"{SEP}", flush=True)
        logger.info("Performing interactive login...")

        try:
            await self.context.clear_cookies()
            logger.info("Cookies cleared \u2014 fresh login")

            for attempt in range(2):
                try:
                    await self.page.goto(
                        "https://idplogin.gep.com",
                        wait_until="domcontentloaded", timeout=60000,
                    )
                    await self.page.wait_for_timeout(5000)
                    url = self.page.url.lower()
                    logger.info("Post-nav URL: %s", url[:120])
                    if "chrome-error" not in url:
                        break
                except Exception as e:
                    logger.warning("Nav attempt %d: %s", attempt + 1, e)
                    await self.page.wait_for_timeout(3000)

            try:
                await self.page.wait_for_url("**idplogin**", timeout=30000)
                logger.info("On login page: %s", self.page.url[:120])
            except Exception:
                logger.warning("Not on idplogin: %s", (self.page.url[:120] if self.page else "?"))
                if "businessnetwork.gep.com" in self.page.url.lower():
                    await self._save_cookies()
                    await self._extract_tokens()
                    return True

            for retry in range(3):
                sel = 'input[id="userId"], input[placeholder="Username"], input[name="Username"]'
                inp = self.page.locator(sel).first
                if await inp.is_visible(timeout=5000):
                    await inp.fill(self.account["username"])
                    logger.info("Username entered")
                    break
                await self.page.wait_for_timeout(2000)
            else:
                logger.warning("Could not find username field")
                return False

            pw_btn = self.page.locator('button:has-text("Login with Password")').first
            if await pw_btn.is_visible(timeout=3000):
                await pw_btn.click()
                logger.info("Login with Password clicked")
                await self.page.wait_for_timeout(3000)

            for retry in range(5):
                pw_inp = self.page.locator(
                    'input[placeholder="Password"], input[name="Password"], '
                    'input[id="Password"], input[type="password"]'
                ).first
                if await pw_inp.is_visible(timeout=5000):
                    await pw_inp.fill(self.account["password"])
                    logger.info("Password entered")
                    break
                await self.page.wait_for_timeout(2000)
            else:
                logger.warning("Could not find password field")
                return False

            login_btn = self.page.locator(
                'button[type="submit"], input[type="submit"], '
                'button:has-text("Sign In"), button:has-text("Login")'
            ).first
            if await login_btn.is_visible(timeout=3000):
                await login_btn.click()
            else:
                await pw_inp.press("Enter")
            logger.info("Login submitted, waiting for SSO redirect to businessnetwork.gep.com...")

            try:
                await self.page.wait_for_url("**businessnetwork**", timeout=60000)
                logger.info("SSO post-login redirect to BizNet: %s", self.page.url[:120])
            except Exception:
                logger.warning("SSO post-login redirect timed out")

            for i in range(10):
                await self.page.wait_for_timeout(2000)
                url = self.page.url.lower()
                if "businessnetwork.gep.com" in url and "login" not in url:
                    logger.info("On BizNet: %s", url[:120])
                    break

            await self._save_cookies()
            url = self.page.url.lower()

            if "idplogin.gep.com" in url:
                print(patrol_section("Login", False, "still on login page — bad credentials?"), flush=True)
                logger.warning("Still on login page after submission")
                print(f"{SEP}\n", flush=True)
                return False

            print(patrol_section("Login", True, f"authenticated on {url[:60]}"), flush=True)

            self._current_url = self.page.url
            await self._extract_tokens()
            cookie_count = len(self._tokens.get("cookies", []))
            print(patrol_section("Login complete", cookie_count > 10, f"URL={self._current_url[:60]} cookies={cookie_count}"), flush=True)
            logger.info("Login complete: URL=%s cookies=%d", self._current_url[:80], cookie_count)
            print(f"{SEP}\n", flush=True)
            return cookie_count > 10

        except Exception as e:
            print(patrol_section("Login", False, f"error: {e}"), flush=True)
            logger.error("Interactive login error: %s", e)
            print(f"{SEP}\n", flush=True)
            return False

    async def _navigate_to_smartgep_event(self):
        """Navigate to a SmartGEP SPA event detail page to extract netsessionid.
        The netsessionid only exists in the AngularJS SPA context on smart.gep.com.
        If navigation fails (smart.gep.com unreachable from VPS), recover to biznet."""
        if not self.page:
            return
        evt = self._get_anchor_event()
        if not evt:
            logger.warning("No anchor event URL available — staying on biznet")
            return
        try:
            print(patrol_section("SmartGEP event nav", False, f"navigating to extract netsessionid..."), flush=True)
            await self.page.goto(
                evt["full_url"],
                wait_until="domcontentloaded", timeout=RELOAD_TIMEOUT,
            )
            await self.page.wait_for_timeout(SETTLE_TIME)
            self._current_url = self.page.url
            await self._extract_tokens()
            nsid = self._tokens.get("netsessionid")
            if nsid:
                print(patrol_section("SmartGEP event nav", True, f"nsid={nsid[:12]}—"), flush=True)
                logger.info("SmartGEP SPA booted — netsessionid extracted: %s", nsid[:12])
            else:
                print(patrol_section("SmartGEP event nav", False, "nsid still empty — SPA may not have booted"), flush=True)
                logger.warning("No netsessionid after SmartGEP nav — SPA may not be loading")
        except Exception as e:
            print(patrol_section("SmartGEP event nav", False, str(e)), flush=True)
            logger.error("SmartGEP event navigation failed: %s", e)
        # Recover: if we got stuck on SSO or error page, go back to biznet
        if self.page:
            current_url = self.page.url.lower() if self.page else ""
            if any(h in current_url for h in ["smart-sts", "idplogin", "chrome-error", "login", "authenticate"]):
                logger.warning("SmartGEP nav left us on SSO/error — navigating back to biznet")
                try:
                    await self.page.goto(
                        "https://businessnetwork.gep.com/BusinessNetwork/Landing/v2#/bn-landing",
                        wait_until="domcontentloaded", timeout=45000,
                    )
                    await self.page.wait_for_timeout(5000)
                    self._current_url = self.page.url
                    logger.info("Recovered to biznet: %s", self._current_url[:80])
                except Exception as recovery_e:
                    logger.error("Recovery to biznet failed: %s", recovery_e)

    def _load_event_id_map(self) -> dict:
        """Load the event_id_map.json to resolve event_number → event_id + doc_url."""
        search_dirs = [
            Path("/home/the_bomb/orkes_ds/data"),
            DATA_DIR,
        ]
        for data_dir in search_dirs:
            eid_path = data_dir / "pricesheet_extract" / "event_id_map.json"
            if eid_path.exists():
                try:
                    return json.loads(eid_path.read_text())
                except Exception as e:
                    logger.warning("Failed to load event_id_map: %s", e)
        return {}

    def _get_anchor_event(self) -> Optional[dict]:
        """Load a known SmartGEP event detail URL from saved data.
        Returns BizNet landing as fallback."""
        search_dirs = [
            Path("/home/the_bomb/orkes_ds/data"),
            DATA_DIR,
        ]
        try:
            for data_dir in search_dirs:
                eid_path = data_dir / "pricesheet_extract" / "event_id_map.json"
                if eid_path.exists():
                    events = json.loads(eid_path.read_text())
                    for evt_num, evt_data in events.items():
                        if "doc_url" in evt_data:
                            logger.info("Anchor event from %s: %s", eid_path, evt_num)
                            return {
                                "event_number": evt_num,
                                "full_url": f"https://smart.gep.com{evt_data['doc_url']}",
                            }
        except Exception as e:
            logger.warning("Failed to load anchor event: %s", e)
        return None

    async def _refresh_page(self):
        """Refresh BizNet session to keep cookies alive."""
        if not self.page:
            logger.warning("No page to refresh")
            return
        print(f"\n{SEP}", flush=True)
        print(f"  \U0001f36a Cookie Monster Session Refresh", flush=True)
        print(f"{SEP}", flush=True)
        try:
            await self.page.goto(
                "https://businessnetwork.gep.com/",
                wait_until="domcontentloaded", timeout=RELOAD_TIMEOUT,
            )
            await self.page.wait_for_timeout(SETTLE_TIME)
            self._current_url = self.page.url
            await self._extract_tokens()
            url_lower = self.page.url.lower() if self.page else ""
            if any(h in url_lower for h in ["login", "idplogin", "authenticate", "smart-sts"]):
                print(patrol_section("Session refresh", False, "expired — re-logging in"), flush=True)
                print(f"{SEP}\n", flush=True)
                logger.warning("Session expired — re-logging in...")
                await self._ensure_login()
            else:
                cook_count = len(self._tokens.get("cookies", []))
                print(patrol_section("Session refresh", True, f"cookies={cook_count}"), flush=True)
                print(f"{SEP}\n", flush=True)
                # Health watchdog: verify browser can make authenticated requests
                try:
                    resp = await asyncio.wait_for(
                        self.page.request.get("https://businessnetwork.gep.com/", timeout=15000),
                        timeout=20.0,
                    )
                    if resp.status < 400:
                        logger.info("Health watchdog OK: %s", resp.status)
                    else:
                        logger.warning("Health watchdog returned %s — session may be stale", resp.status)
                except Exception as e:
                    logger.warning("Health watchdog failed: %s — session may be dead", type(e).__name__)
        except Exception as e:
            print(patrol_section("Session refresh", False, str(e)), flush=True)
            print(f"{SEP}\n", flush=True)
            logger.error("Page refresh failed: %s", e)

    async def _extract_tokens(self):
        if not self.page:
            return
        tokens: Dict[str, Any] = {
            "netsessionid": "",
            "requestverificationtoken": "",
            "oloc": "",
            "account": self.account_id,
        }

        try:
            nsid = await self.page.evaluate(
                "() => { try { return rfx.resources.constants.netsessionid || ''; } catch(e) { return ''; } }"
            )
            if nsid:
                tokens["netsessionid"] = nsid
        except Exception:
            pass

        try:
            rvt = await self.page.evaluate(
                "() => { try { var m=document.querySelector('input[name=\"__RequestVerificationToken\"]'); "
                "if(m) return m.value; "
                "if(window.rfx&&window.rfx.resources&&window.rfx.resources.constants) "
                "return window.rfx.resources.constants.requestVerificationToken||''; "
                "return ''; } catch(e) { return ''; }"
            )
            if rvt:
                tokens["requestverificationtoken"] = rvt
        except Exception:
            pass

        try:
            m = re.search(r"[?&]oloc=(\d+)", self.page.url)
            if m:
                tokens["oloc"] = m.group(1)
        except Exception:
            pass

        try:
            raw_cookies = await self.context.cookies()
            tokens["cookies"] = []
            for c in raw_cookies:
                domain = c.get("domain", "") or ""
                entry = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": domain.lstrip(".") if domain else "",
                    "path": c.get("path", "/"),
                    "secure": c.get("secure", True),
                    "httpOnly": c.get("httpOnly", False),
                    "sameSite": c.get("sameSite", "None"),
                }
                if domain:
                    entry["url"] = f"https://{domain.lstrip('.')}"
                tokens["cookies"].append(entry)
        except Exception:
            tokens["cookies"] = []

        self._tokens = tokens
        self._last_refresh = time.time()
        nsid = tokens.get("netsessionid") or "NONE"
        cook_count = len(tokens.get("cookies", []))
        logger.info(
            "Tokens refreshed: nsid=%s oloc=%s cookies=%d",
            nsid[:12],
            tokens.get("oloc") or "?",
            cook_count,
        )

    async def _refresh_loop(self):
        from datetime import datetime, timezone
        while True:
            await asyncio.sleep(REFRESH_INTERVAL)
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n  [{ts}] \U0001f36a Cookie Monster scheduled refresh ({REFRESH_INTERVAL}s interval)", flush=True)
            await self._refresh_page()

    async def _reload(self, target_url: Optional[str] = None):
        if not self.page:
            return self._tokens
        try:
            if target_url:
                await self.page.goto(target_url, wait_until="domcontentloaded", timeout=RELOAD_TIMEOUT)
            else:
                await self.page.reload(wait_until="domcontentloaded")
            await self.page.wait_for_timeout(SETTLE_TIME)
        except Exception as e:
            logger.warning("Reload failed: %s", e)
        await self._save_cookies()
        await self._extract_tokens()
        return self._tokens

    async def _read_post_body(self, reader: asyncio.StreamReader, headers: Dict[str, str]) -> bytes:
        cl = int(headers.get("content-length", "0"))
        if cl > 0 and cl < 10_000_000:
            return await reader.readexactly(cl)
        return b""

    async def _parse_http_request(self, reader: asyncio.StreamReader):
        data = await reader.readuntil(b"\n")
        request_line = data.decode("utf-8", errors="replace").strip()
        if not request_line:
            return None, None, {}, b""
        method, path, _ = request_line.split(" ", 2)
        method = method.upper()
        headers = {}
        while True:
            line = await reader.readline()
            if line == b"\r\n" or line == b"\n" or not line:
                break
            raw = line.decode("utf-8", errors="replace").strip()
            if ":" in raw:
                k, v = raw.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        body = await self._read_post_body(reader, headers)
        return method, path, headers, body

    def _send_http(self, writer, status: int, body_json: dict | list):
        resp = json.dumps(body_json, default=str)
        resp_bytes = f"HTTP/1.1 {status} {'OK' if 200 <= status < 300 else 'Error'}\r\n" \
                     f"Content-Type: application/json\r\n" \
                     f"Content-Length: {len(resp)}\r\n" \
                     f"Access-Control-Allow-Origin: *\r\n" \
                     f"Connection: close\r\n\r\n{resp}"
        writer.write(resp_bytes.encode("utf-8"))

    async def _handle_listing(self, request: dict) -> dict:
        url = request.get("url", "")
        body = request.get("body", {})
        page = request.get("page", 1)
        page_size = request.get("size", 1000)
        method = request.get("method", "POST").upper()
        timeout_ms = min(int(request.get("timeout", 60000)), 120000)

        if not url:
            return {"error": "url is required", "status": 400}

        merged_body = json.loads(json.dumps(body))
        if isinstance(merged_body, dict):
            merged_body["PageIndex"] = page
            merged_body["PageSize"] = page_size

        return await asyncio.to_thread(
            self._http_fetch, url, method,
            {"Content-Type": "application/json", "Accept": "application/json"},
            json.dumps(merged_body) if isinstance(merged_body, dict) else None,
            max(1, timeout_ms // 1000),
        )

    def _http_fetch(self, url: str, method: str = "GET",
                              headers: Optional[dict] = None,
                              body: Optional[str] = None,
                              timeout: int = 30) -> dict:
        """Server-side HTTP request using stored cookies as fallback."""
        try:
            import http.client
            import ssl
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query

            cookie_str = "; ".join(
                f"{c['name']}={c['value']}"
                for c in self._tokens.get("cookies", [])
                if host and (host in (c.get("domain", "") or "") or not c.get("domain"))
            )

            conn_kw = {"timeout": timeout}
            if parsed.scheme == "https":
                ctx = ssl.create_default_context()
                ctx.check_hostname = True
                ctx.verify_mode = ssl.CERT_REQUIRED
                conn_kw["context"] = ctx

            conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
            conn = conn_cls(host, port, **conn_kw)

            req_headers = dict(headers or {})
            if method in ("POST", "PUT", "PATCH"):
                req_headers.setdefault("Content-Type", "application/json")
            if cookie_str:
                req_headers.setdefault("Cookie", cookie_str)
            req_headers.setdefault("Accept", "application/json, */*")
            req_headers.setdefault("User-Agent", (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ))

            conn.request(method, path, body=body or None, headers=req_headers)
            resp = conn.getresponse()
            resp_body = resp.read()
            resp_text = resp_body.decode("utf-8", errors="replace")
            parsed_json = None
            try:
                parsed_json = json.loads(resp_text)
            except Exception:
                pass
            conn.close()

            return {
                "status": resp.status,
                "statusText": resp.reason or "",
                "contentType": resp.getheader("content-type", ""),
                "body": resp_text,
                "bodyLength": len(resp_text),
                "bodyJson": parsed_json,
            }
        except Exception as e:
            return {"error": f"http_fetch_failed: {e}", "status": 0}

    async def _handle_boq_extract(self, request: dict) -> dict:
        """Navigate to SmartGEP event, intercept APIs, fetch child sheets, parse BoQ."""
        doc_url = request.get("doc_url", "")
        event_number = request.get("event_number", "")
        event_id = request.get("event_id", "")
        partner_code = request.get("partner_code", "NzAwMjE3OTA1")
        oloc = request.get("oloc", "219")

        # Resolve event_number → event_id + doc_url from saved event_id_map
        if event_number and (not doc_url or not event_id):
            event_map = self._load_event_id_map()
            if event_number in event_map:
                entry = event_map[event_number]
                if not doc_url and entry.get("doc_url"):
                    doc_url = entry["doc_url"]
                if not event_id and entry.get("event_id"):
                    event_id = entry["event_id"]
                logger.info("[boq-extract] Resolved %s → id=%s url=%s", event_number, event_id, doc_url[:60])

        if not doc_url or not event_id:
            return {"error": "doc_url and event_id required", "status": 400}
        if not doc_url.startswith("http"):
            doc_url = f"https://smart.gep.com{doc_url}"

        psevent_body: Optional[str] = None
        pricesheet_bodies: Dict[str, str] = {}
        pricedatasheet_bodies: Dict[str, str] = {}

        def _extract_id_from_url(url: str, pattern: str) -> str:
            try:
                return url.split(pattern)[-1].split("?")[0].split("/")[0]
            except Exception:
                return ""

        async def _route(route):
            url = route.request.url
            try:
                resp = await route.fetch()
                body = await resp.text()
            except Exception:
                await route.continue_()
                return

            nonlocal psevent_body
            if "/data/psevent/" in url and "action" not in url:
                if event_id in url and len(body) > 10:
                    psevent_body = body
            elif "/data/doGetPricesheet" in url or "/action/doGetPricesheet" in url:
                ps_id = _extract_id_from_url(url, "doGetPricesheet")
                if ps_id:
                    pricesheet_bodies[ps_id] = body
            elif "/data/doGetPricedatasheet" in url or "/action/doGetPricedatasheet" in url:
                ds_id = _extract_id_from_url(url, "doGetPricedatasheet")
                if ds_id:
                    pricedatasheet_bodies[ds_id] = body
            elif ("/data/pricesheet/" in url and "/data/pricedatasheet/" not in url
                  and "/data/psevent/" not in url):
                ps_id = _extract_id_from_url(url, "/data/pricesheet/")
                if ps_id:
                    pricesheet_bodies[ps_id] = body
            elif "/data/pricedatasheet/" in url:
                ds_id = _extract_id_from_url(url, "/data/pricedatasheet/")
                if ds_id:
                    pricedatasheet_bodies[ds_id] = body

            await route.fulfill(response=resp)

        await self.page.route("**/smart.gep.com/data/psevent/**", _route)
        await self.page.route("**/smart.gep.com/data/pricesheet/**", _route)
        await self.page.route("**/smart.gep.com/data/pricedatasheet/**", _route)
        await self.page.route("**/smart.gep.com/**/doGetPricesheet**", _route)
        await self.page.route("**/smart.gep.com/**/doGetPricedatasheet**", _route)

        logger.info("[boq-extract] Navigating: %s", event_number)
        try:
            await self.page.goto(doc_url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            logger.warning("[boq-extract] Nav error: %s — continuing", e)

        self._current_url = self.page.url
        logger.info("[boq-extract] Post-nav URL: %s", self._current_url[:150])

        # If we landed on BizNet landing (SSO redirect), wait for client-side redirect
        if "businessnetwork.gep.com" in self._current_url.lower() and "/landing" in self._current_url.lower():
            logger.info("[boq-extract] On BizNet landing — waiting for smart.gep.com redirect")
            for i in range(30):
                await asyncio.sleep(2)
                current = self.page.url
                if "smart.gep.com" in current.lower() and "sts" not in current.lower():
                    logger.info("[boq-extract] Redirected to smart.gep.com after %ds", (i+1)*2)
                    self._current_url = current
                    break
                # Also check for iframes
                if i == 5:
                    frames = self.page.frames
                    for f in frames:
                        fu = f.url
                        if "smart.gep.com" in fu and "sts" not in fu:
                            logger.info("[boq-extract] Found smart.gep.com in iframe: %s", fu[:100])
                            break

        if not psevent_body:
            # Wait more for SPA to boot and APIs to fire
            for i in range(10):
                await asyncio.sleep(2)
                if psevent_body:
                    logger.info("[boq-extract] psevent captured after %ds wait", (i+1)*2 + 8)
                    break

        if not psevent_body:
            self._current_url = self.page.url
            return {"error": "no_psevent_captured", "page_url": self.page.url[:200], "status": 502}

        price_sheet_ids = []
        child_sheet_ids = []
        try:
            ps_data = json.loads(psevent_body)
            for ps in ps_data.get("priceSheets", []):
                psid = ps.get("_id", "")
                if psid:
                    price_sheet_ids.append(psid)
            logger.info("[boq-extract] psevent: %d price sheets", len(price_sheet_ids))
        except json.JSONDecodeError:
            pass

        materials_selectors = [
            'a:has-text("Materials")', 'a:has-text("Material")',
            'a:has-text("Price Sheet")', 'a:has-text("PriceSheets")',
            'li:has-text("Materials")', 'li:has-text("Material")',
            'button:has-text("Materials")', 'button:has-text("Material")',
            'span:has-text("Materials")', 'a[href*="material"]', 'a[href*="price"]',
        ]
        for sel in materials_selectors:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    await el.click(timeout=5000)
                    logger.info("[boq-extract] Clicked: %s", sel)
                    await asyncio.sleep(6)
                    break
            except Exception:
                continue

        for ps_id, body in pricesheet_bodies.items():
            try:
                ps = json.loads(body)
                buyer_ids = ps.get("buyerDataSheets", [])
                supplier_ids = ps.get("supplierDataSheets", [])
                for cid in buyer_ids + supplier_ids:
                    cid_str = str(cid)
                    if cid_str and cid_str not in child_sheet_ids:
                        child_sheet_ids.append(cid_str)
                logger.info("[boq-extract] Pricesheet %s: %dB + %dS children",
                           ps_id[:12], len(buyer_ids), len(supplier_ids))
            except Exception:
                pass

        logger.info("[boq-extract] Child sheet IDs to fetch: %d", len(child_sheet_ids))

        child_fetched = 0
        for cid in child_sheet_ids:
            if cid in pricedatasheet_bodies or child_fetched >= 100:
                continue
            result = await self.page.evaluate("""
            async (args) => {
                const {cid, pc, oloc} = args;
                const urls = [
                    '/action/doGetPricedatasheet/' + cid + '?oloc=' + oloc + '&c=' + pc,
                    '/data/pricedatasheet/' + cid + '?oloc=' + oloc + '&c=' + pc,
                ];
                for (const url of urls) {
                    try {
                        const injector = angular.element(document.body).injector();
                        const $http = injector.get('$http');
                        const resp = await $http.post(url);
                        if (resp.data && typeof resp.data === 'object') {
                            const text = JSON.stringify(resp.data);
                            if (text.length > 200) return {ok: true, body: text, size: text.length};
                        }
                    } catch(e) {}
                }
                for (const url of urls) {
                    try {
                        const r = await fetch(url, {
                            method: 'GET', credentials: 'include',
                            headers: {'Accept': 'application/json'}
                        });
                        const text = await r.text();
                        if (r.ok && text.length > 200 && text.startsWith('{'))
                            return {ok: true, body: text, size: text.length};
                    } catch(e) {}
                }
                return {ok: false};
            }
            """, {"cid": cid, "pc": partner_code, "oloc": oloc})
            if result and result.get("ok"):
                pricedatasheet_bodies[cid] = result["body"]
                child_fetched += 1

        logger.info("[boq-extract] Child sheets fetched: %d", child_fetched)

        await self.page.unroute("**/smart.gep.com/data/psevent/**")
        await self.page.unroute("**/smart.gep.com/data/pricesheet/**")
        await self.page.unroute("**/smart.gep.com/data/pricedatasheet/**")
        await self.page.unroute("**/smart.gep.com/**/doGetPricesheet**")
        await self.page.unroute("**/smart.gep.com/**/doGetPricedatasheet**")

        # Parse items
        from smartgep_api import PricesheetRowParser
        all_items = []
        seen_dedup = set()
        all_bodies = list(pricesheet_bodies.values()) + list(pricedatasheet_bodies.values())

        for body in all_bodies:
            try:
                data = json.loads(body) if isinstance(body, str) else body
            except Exception:
                continue
            try:
                parser = PricesheetRowParser(data)
                specs = parser.extract_material_specs()
                for spec in specs:
                    key = str(spec.get("item_code", "")) + str(spec.get("description", ""))
                    if key in seen_dedup:
                        continue
                    seen_dedup.add(key)
                    all_items.append(spec)
            except Exception:
                items = data.get("dataSheet", {})
                rows = items.get("dataRows", items.get("rows", [])) or []
                schema = data.get("colSchema", items.get("colSchema", {}))
                cols = schema.get("columns", []) if isinstance(schema, dict) else schema
                col_map = {}
                for i, c in enumerate(cols):
                    alias = c.get("alias", "")
                    name = c.get("name", "")
                    if alias:
                        col_map[alias] = name
                for row in rows:
                    item = {}
                    if isinstance(row, dict):
                        for alias, name in col_map.items():
                            if alias in row and row[alias]:
                                item[name] = row[alias]
                        for vk, name in [("v1","description"),("v2","item_code"),("v3","uom"),("v7","quantity")]:
                            if name not in item and vk in row and row[vk]:
                                item[name] = row[vk]
                    elif isinstance(row, list):
                        for alias, name in col_map.items():
                            for i, c in enumerate(cols):
                                if c.get("alias") == alias and i < len(row) and row[i]:
                                    item[name] = row[i]
                    if item.get("description") or item.get("item_code"):
                        all_items.append(item)

        logger.info("[boq-extract] Total items parsed: %d", len(all_items))

        # Navigate back to BizNet to recover SSO
        try:
            await self.page.goto(
                "https://businessnetwork.gep.com/",
                wait_until="domcontentloaded", timeout=45000,
            )
            await asyncio.sleep(5)
            self._current_url = self.page.url
            await self._extract_tokens()
            logger.info("[boq-extract] Recovered to BizNet: %s", self._current_url[:80])
        except Exception as e:
            logger.warning("[boq-extract] Recovery to BizNet failed: %s", e)

        return {
            "event_number": event_number,
            "event_id": event_id,
            "price_sheet_ids": price_sheet_ids,
            "child_sheet_ids": child_sheet_ids,
            "pricesheet_count": len(pricesheet_bodies),
            "child_sheets_fetched": len(pricedatasheet_bodies),
            "items_count": len(all_items),
            "items": all_items,
            "status": 200,
        }

    async def _handle_nav_eval(self, request: dict) -> dict:
        """Navigate browser to target URL, wait, then run code in page context."""
        nav_url = request.get("nav_url", "")
        code = request.get("code", "")
        wait_ms = int(request.get("wait_ms", 8000))
        timeout_ms = int(request.get("timeout", 45000))
        if not nav_url:
            return {"error": "nav_url is required", "status": 400}
        if not code:
            return {"error": "code is required", "status": 400}
        try:
            await self.page.goto(nav_url, wait_until="domcontentloaded",
                                  timeout=timeout_ms)
            await asyncio.sleep(wait_ms / 1000)
            self._current_url = self.page.url
            logger.info("/nav-eval nav=%s... code=%s... url=%s",
                        nav_url[:80], code[:60], self.page.url[:80])
            result = await self.page.evaluate(code)
            logger.info("/nav-eval result=%s", str(result)[:100])
            return {"result": result, "page_url": self.page.url[:200], "status": 200}
        except Exception as e:
            logger.error("/nav-eval error: %s", e)
            return {"error": str(e), "page_url": (self.page.url[:200] if self.page else ""), "status": 500}

    async def _handle_eval(self, request: dict) -> dict:
        code = request.get("code", "")
        if not code:
            return {"error": "code is required", "status": 400}
        try:
            result = await self.page.evaluate(code)
            logger.info("/eval code=%s... result=%s", code[:60], str(result)[:80])
            return {"result": result, "status": 200}
        except Exception as e:
            logger.error("/eval error: %s", e)
            return {"error": str(e), "status": 500}

    async def _handle_browse_fetch(self, request: dict) -> dict:
        """Layered fetch with fallback: browser request → HTTP → re-auth.

        Layer 1 (browser request): Use Playwright's page.request.fetch() which
        uses the browser's cookie jar + storage state (full multi-domain SSO).
        Handles POST, PUT, redirects natively.

        Layer 2 (HTTP): Direct http.client with all cookies injected.

        Layer 3 (re-auth): Trigger interactive login, retry Layer 1.
        """
        url = request.get("url", "")
        fetch_method = request.get("method", "GET").upper()
        req_headers = request.get("headers", {})
        req_body = request.get("body", None)
        timeout_ms = min(int(request.get("timeout", 30000)), 120000)

        if not url:
            return {"error": "url is required", "status": 400}

        layers_attempted = []

        # ── Layer 1: Browser request (Playwright cookie jar) ───────────
        if self.page:
            try:
                options = {
                    "method": fetch_method,
                    "timeout": timeout_ms,
                }
                if req_headers:
                    options["headers"] = req_headers
                if req_body is not None:
                    options["data"] = req_body if isinstance(req_body, dict) else str(req_body)

                response = await asyncio.wait_for(
                    self.page.request.fetch(url, **options),
                    timeout=timeout_ms / 1000 + 5,
                )
                body_bytes = await asyncio.wait_for(response.body(), timeout=10.0)
                text = body_bytes.decode("utf-8", errors="replace")
                json_body = None
                try:
                    json_body = json.loads(text)
                except Exception:
                    pass
                layers_attempted.append("browser-request")
                result = {
                    "status": response.status,
                    "statusText": response.status_text,
                    "headers": dict(response.headers),
                    "body": text,
                    "bodyJson": json_body,
                    "_layer": "browser-request",
                }
                logger.info("/browse-fetch L1 (browser-request) OK: %s → %s", url[:80], response.status)
                return result
            except asyncio.TimeoutError:
                logger.warning("/browse-fetch L1 (browser-request) timeout: %s", url[:80])
            except Exception as e:
                logger.warning("/browse-fetch L1 (browser-request) error: %s: %s", type(e).__name__, str(e)[:120])

        # ── Layer 2: Direct HTTP with all cookies ─────────────────────
        try:
            all_cookies = self._tokens.get("cookies", [])
            cookie_str = "; ".join(
                f"{c['name']}={c['value']}" for c in all_cookies if c.get("name")
            )
            merged_headers = dict(req_headers)
            if cookie_str:
                merged_headers["Cookie"] = cookie_str

            http_result = await asyncio.to_thread(
                self._http_fetch, url, fetch_method,
                merged_headers,
                json.dumps(req_body) if req_body and isinstance(req_body, dict) else None,
                max(1, timeout_ms // 1000),
            )
            status_code = http_result.get("status_code", http_result.get("status", 0))
            if status_code and status_code < 400:
                layers_attempted.append("http")
                http_result["_layer"] = "http"
                logger.info("/browse-fetch L2 (http) OK: %s → %s (cookies=%d)", url[:80], status_code, len(all_cookies))
                return http_result
            else:
                logger.info("/browse-fetch L2 response: %s (falling back)", status_code)
        except Exception as e:
            logger.warning("/browse-fetch L2 error: %s", type(e).__name__)

        # ── Layer 3: Re-auth + retry browser ──────────────────────────
        try:
            logger.info("/browse-fetch L3: re-authenticating...")
            reauth_ok = await self._ensure_login()
            if reauth_ok and self.page:
                options = {
                    "method": fetch_method,
                    "timeout": timeout_ms,
                }
                if req_headers:
                    options["headers"] = req_headers
                if req_body is not None:
                    options["data"] = req_body if isinstance(req_body, dict) else str(req_body)
                response = await asyncio.wait_for(
                    self.page.request.fetch(url, **options),
                    timeout=timeout_ms / 1000 + 5,
                )
                body_bytes = await asyncio.wait_for(response.body(), timeout=10.0)
                text = body_bytes.decode("utf-8", errors="replace")
                json_body = None
                try:
                    json_body = json.loads(text)
                except Exception:
                    pass
                layers_attempted.append("reauth-browser")
                result = {
                    "status": response.status,
                    "statusText": response.status_text,
                    "headers": dict(response.headers),
                    "body": text,
                    "bodyJson": json_body,
                    "_layer": "reauth-browser",
                }
                logger.info("/browse-fetch L3 (reauth) OK: %s → %s", url[:80], response.status)
                return result
        except Exception as e:
            logger.warning("/browse-fetch L3 error: %s", type(e).__name__)

        return {
            "error": "all layers exhausted",
            "layers_attempted": layers_attempted,
            "status": 502,
        }

    async def _handle_fetch(self, request: dict) -> dict:
        url = request.get("url", "")
        fetch_method = request.get("method", "GET").upper()
        req_headers = request.get("headers", {})
        req_body = request.get("body", None)
        timeout_ms = min(int(request.get("timeout", 30000)), 120000)

        if not url:
            return {"error": "url is required", "status": 400}

        logger.info("HTTP fetch for %s (%d cookies)", url[:100], len(self._tokens.get("cookies", [])))
        result = await asyncio.to_thread(
            self._http_fetch, url, fetch_method,
            req_headers, json.dumps(req_body) if req_body else None,
            max(1, timeout_ms // 1000),
        )
        return result

    async def _handle_http(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            method, path, headers, body_bytes = await self._parse_http_request(reader)
            if method is None:
                writer.close()
                return

            path_only = path.split("?")[0]

            if method == "GET" and path_only == "/health":
                has_nsid = bool(self._tokens.get("netsessionid"))
                has_cookies = len(self._tokens.get("cookies", [])) > 0
                self._send_http(writer, 200, {
                    "alive": True if (has_nsid or has_cookies) and self.page else False,
                    "uptime": int(time.monotonic() - self._start_time),
                    "account": self.account_id,
                    "page_url": (self.page.url[:200] if self.page else ""),
                    "cookies_count": len(self._tokens.get("cookies", [])),
                    "tokens_valid": has_nsid,
                    "spa_available": has_nsid,
                    "last_refresh": (
                        datetime.fromtimestamp(self._last_refresh, tz=timezone.utc).isoformat()
                        if self._last_refresh else ""
                    ),
                })

            elif method == "GET" and path_only == "/tokens":
                self._send_http(writer, 200, self._tokens)

            elif method == "POST" and path_only == "/reload":
                qs = path.split("?", 1)[1] if "?" in path else ""
                parsed = urllib.parse.parse_qs(qs)
                target_url = parsed.get("url", [None])[0]
                tokens = await self._reload(target_url)
                self._send_http(writer, 200, {"message": "reload complete", "tokens": tokens})

            elif method == "POST" and path_only == "/fetch":
                if not self.page:
                    self._send_http(writer, 503, {"error": "browser_not_ready"})
                    return
                request = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                result = await self._handle_fetch(request)
                status_code = result.get("status", 0)
                if status_code and status_code >= 200:
                    self._send_http(writer, status_code, result)
                elif result.get("error"):
                    self._send_http(writer, 502, result)
                else:
                    self._send_http(writer, 200, result)

            elif method == "POST" and path_only == "/listing":
                if not self.page:
                    self._send_http(writer, 503, {"error": "browser_not_ready"})
                    return
                request = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                result = await self._handle_listing(request)
                status_code = result.get("status", 0)
                if status_code and status_code >= 200:
                    self._send_http(writer, status_code, result)
                elif result.get("error"):
                    self._send_http(writer, 502, result)
                else:
                    self._send_http(writer, 200, result)

            elif method == "POST" and path_only == "/boq-extract":
                if not self.page:
                    self._send_http(writer, 503, {"error": "browser_not_ready"})
                    return
                request = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                result = await self._handle_boq_extract(request)
                status_code = result.get("status", 0)
                if status_code and status_code >= 200:
                    self._send_http(writer, status_code, result)
                elif result.get("error"):
                    self._send_http(writer, 502, result)
                else:
                    self._send_http(writer, 200, result)

            elif method == "POST" and path_only == "/nav-eval":
                if not self.page:
                    self._send_http(writer, 503, {"error": "browser_not_ready"})
                    return
                request = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                result = await self._handle_nav_eval(request)
                self._send_http(writer, 200, result)

            elif method == "POST" and path_only == "/eval":
                if not self.page:
                    self._send_http(writer, 503, {"error": "browser_not_ready"})
                    return
                request = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                result = await self._handle_eval(request)
                self._send_http(writer, 200, result)

            elif method == "POST" and path_only == "/browse-fetch":
                if not self.page:
                    self._send_http(writer, 503, {"error": "browser_not_ready"})
                    return
                request = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                result = await self._handle_browse_fetch(request)
                status_code = result.get("status", 0)
                if status_code and status_code >= 200:
                    self._send_http(writer, status_code, result)
                else:
                    self._send_http(writer, 502, result)

            else:
                self._send_http(writer, 404, {"error": "not_found", "path": path, "method": method})

        except Exception as e:
            logger.error("HTTP handler error: %s", e)
            try:
                self._send_http(writer, 500, {"error": str(e)})
            except Exception:
                pass
        finally:
            try:
                writer.close()
            except Exception:
                pass


async def main():
    parser = argparse.ArgumentParser(description="permauth — Persistent Playwright Auth Daemon")
    parser.add_argument("--account", default="consurv", help="Account ID")
    parser.add_argument("--port", type=int, default=9876, help="HTTP API port")
    args = parser.parse_args()

    daemon = PermauthDaemon(args.account, port=args.port)
    await daemon.start()


if __name__ == "__main__":
    asyncio.run(main())
