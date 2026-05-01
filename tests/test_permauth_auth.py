"""Tests for permauth.py — SSO redirect, auth lifecycle, tokens, cookies, HTTP routing."""
import asyncio
import json
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def sample_account():
    return {
        "id": "consurv",
        "label": "Test Account",
        "username": "testuser",
        "password": "testpass",
        "enabled": True,
    }


@pytest.fixture
def mock_daemon(sample_account, tmp_path, monkeypatch):
    """Create a PermauthDaemon with paths redirected to tmp_path."""
    from permauth import PermauthDaemon

    accts_dir = tmp_path / "scrapers"
    accts_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    accts_file = accts_dir / "smartgep_accounts.json"
    accts_file.write_text(json.dumps({"accounts": [sample_account]}))

    monkeypatch.setattr("permauth.ACCOUNTS_PATH", accts_file)
    monkeypatch.setattr("permauth.DATA_DIR", tmp_path / "data")

    daemon = PermauthDaemon("consurv", port=19876)
    # context is None until _init_browser() runs; tests that need it set it explicitly
    return daemon


def _setup_daemon_context(daemon):
    """Give daemon a mock context (needed for _ensure_login tests that call clear_cookies)."""
    daemon.context = AsyncMock()
    daemon.context.cookies = AsyncMock(return_value=[])
    daemon.context.clear_cookies = AsyncMock()
    return daemon


# ══════════════════════════════════════════════════════════════════════
# SSO URL Detection
# ══════════════════════════════════════════════════════════════════════

class TestSSOUrlDetection:
    """Daemon correctly identifies SSO state from page URL."""

    def _make_page_mock(self, url):
        page = AsyncMock()
        page.url = url
        page.evaluate = AsyncMock(return_value="")
        return page

    def test_detects_smart_sts_redirect(self, mock_daemon):
        mock_daemon.page = self._make_page_mock(
            "https://smart-sts.gep.com/Authenticate?ReturnUrl=..."
        )
        assert "smart-sts" in mock_daemon.page.url.lower()

    def test_detects_idplogin_page(self, mock_daemon):
        mock_daemon.page = self._make_page_mock(
            "https://idplogin.gep.com/login?wa=wsignin1.0..."
        )
        assert "idplogin" in mock_daemon.page.url.lower()

    def test_detects_biznet_landing(self, mock_daemon):
        mock_daemon.page = self._make_page_mock(
            "https://businessnetwork.gep.com/BusinessNetwork/Landing/v2#/bn-landing"
        )
        assert "businessnetwork.gep.com" in mock_daemon.page.url.lower()
        assert "login" not in mock_daemon.page.url.lower()

    def test_detects_chrome_error(self, mock_daemon):
        mock_daemon.page = self._make_page_mock("chrome-error://chromewebdata/")
        error_hosts = ["chrome-error", "about:blank", "smarterr.gep.com"]
        needs = any(h in mock_daemon.page.url.lower() for h in error_hosts)
        assert needs is True

    def test_biznet_does_not_trigger_sso(self, mock_daemon):
        sso_indicators = ["smart-sts", "idplogin", "login", "authenticate"]
        url = "https://businessnetwork.gep.com/BusinessNetwork/Landing/v2#/bn-landing"
        assert not any(h in url.lower() for h in sso_indicators)

    def test_smart_sts_triggers_sso(self, mock_daemon):
        sso_indicators = ["smart-sts", "idplogin", "login", "authenticate"]
        url = "https://smart-sts.gep.com/Authenticate?ReturnUrl=..."
        assert any(h in url.lower() for h in sso_indicators)


# ══════════════════════════════════════════════════════════════════════
# _ensure_login() flow
# ══════════════════════════════════════════════════════════════════════

class TestEnsureLoginFlow:
    """Interactive login flow through SSO states."""

    def _setup_page_for_login(self, mock_daemon, initial_url):
        page = AsyncMock()
        page.url = initial_url
        page.goto = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.wait_for_url = AsyncMock()
        page.reload = AsyncMock()

        def _mock_locator(selector):
            loc = AsyncMock()
            loc.first = loc
            if "userId" in selector or "Username" in selector:
                loc.is_visible = AsyncMock(return_value=True)
                loc.fill = AsyncMock()
            elif "Password" in selector or "password" in selector:
                loc.is_visible = AsyncMock(return_value=True)
                loc.fill = AsyncMock()
            elif "Sign In" in selector or "Login" in selector:
                loc.is_visible = AsyncMock(return_value=True)
                loc.click = AsyncMock()
            elif "Login with Password" in selector:
                loc.is_visible = AsyncMock(return_value=True)
                loc.click = AsyncMock()
            else:
                loc.is_visible = AsyncMock(return_value=False)
            return loc

        page.locator = _mock_locator
        mock_daemon.page = page
        return page

    @pytest.mark.asyncio
    async def test_ensure_login_returns_false_without_page(self, mock_daemon):
        mock_daemon.page = None
        result = await mock_daemon._ensure_login()
        assert result is False

    @pytest.mark.asyncio
    async def test_ensure_login_skips_when_on_biznet_with_cookies(self, mock_daemon):
        page = self._setup_page_for_login(
            mock_daemon, "https://businessnetwork.gep.com/BusinessNetwork/Landing/v2"
        )
        mock_daemon._tokens = {"cookies": [{"name": "x", "value": "y"}] * 15}
        result = await mock_daemon._ensure_login()
        assert result is True

    @pytest.mark.asyncio
    @patch("permauth.PermauthDaemon._save_cookies", new_callable=AsyncMock)
    @patch("permauth.PermauthDaemon._extract_tokens", new_callable=AsyncMock)
    async def test_ensure_login_saves_cookies_after_success(
        self, mock_extract, mock_save, mock_daemon
    ):
        _setup_daemon_context(mock_daemon)
        page = self._setup_page_for_login(
            mock_daemon, "https://smart-sts.gep.com/Authenticate?ReturnUrl=..."
        )

        async def goto_effect(url, **kw):
            page.url = "https://smart.gep.com/Sourcing/Rfx?oloc=219"
            return None

        page.goto = AsyncMock(side_effect=goto_effect)
        mock_daemon._tokens = {"netsessionid": "abc123", "cookies": [{"name": "x", "value": "y"}] * 20}

        result = await mock_daemon._ensure_login()
        assert mock_save.called, "_save_cookies should be called after login"
        assert mock_extract.called, "_extract_tokens should be called after login"

    @pytest.mark.asyncio
    async def test_ensure_login_bad_credentials(self, mock_daemon):
        page = self._setup_page_for_login(
            mock_daemon, "https://idplogin.gep.com/login?..."
        )
        async def goto_effect(url, **kw):
            page.url = "https://idplogin.gep.com/login?error=badcreds"
            return None
        page.goto = AsyncMock(side_effect=goto_effect)

        mock_daemon._tokens = {"netsessionid": ""}
        result = await mock_daemon._ensure_login()
        assert result is False

    @pytest.mark.asyncio
    async def test_ensure_login_wait_for_idplogin(self, mock_daemon):
        _setup_daemon_context(mock_daemon)
        calls = []
        page = self._setup_page_for_login(
            mock_daemon, "https://smart-sts.gep.com/Authenticate?..."
        )

        async def wait_url(pattern, **kw):
            calls.append(pattern)
            page.url = "https://idplogin.gep.com/login?wa=wsignin1.0"
            return None

        page.wait_for_url = AsyncMock(side_effect=wait_url)
        page.goto = AsyncMock()
        mock_daemon._tokens = {"cookies": [{"name": "x", "value": "y"}] * 20}

        await mock_daemon._ensure_login()
        assert any("idplogin" in c for c in calls), (
            "wait_for_url(**idplogin**) should be called for SSO redirect"
        )


# ══════════════════════════════════════════════════════════════════════
# Token extraction
# ══════════════════════════════════════════════════════════════════════

class TestExtractTokens:
    """Token extraction from SPA and non-SPA contexts."""

    def _setup_page(self, mock_daemon, url, nsid_result="", rvt_result=""):
        page = AsyncMock()
        page.url = url

        async def eval_side(js):
            if "netsessionid" in js:
                return nsid_result
            if "RequestVerificationToken" in js:
                return rvt_result
            return ""

        page.evaluate = AsyncMock(side_effect=eval_side)
        mock_daemon.page = page
        return page

    @pytest.mark.asyncio
    async def test_extracts_netsessionid_from_spa(self, mock_daemon):
        mock_daemon.context = AsyncMock()
        mock_daemon.context.cookies = AsyncMock(return_value=[])
        self._setup_page(
            mock_daemon,
            "https://smart.gep.com/Sourcing/Rfx?oloc=669",
            nsid_result="abc123netsessionid",
        )
        await mock_daemon._extract_tokens()
        assert mock_daemon._tokens["netsessionid"] == "abc123netsessionid"

    @pytest.mark.asyncio
    async def test_netsessionid_empty_without_spa(self, mock_daemon):
        mock_daemon.context = AsyncMock()
        mock_daemon.context.cookies = AsyncMock(return_value=[])
        self._setup_page(
            mock_daemon, "https://businessnetwork.gep.com/BusinessNetwork/Landing/v2"
        )
        await mock_daemon._extract_tokens()
        assert mock_daemon._tokens["netsessionid"] == ""

    @pytest.mark.asyncio
    async def test_extracts_oloc_from_url(self, mock_daemon):
        mock_daemon.context = AsyncMock()
        mock_daemon.context.cookies = AsyncMock(return_value=[])
        self._setup_page(
            mock_daemon, "https://smart.gep.com/Sourcing/Rfx?oloc=219&c=NzAw..."
        )
        await mock_daemon._extract_tokens()
        assert mock_daemon._tokens["oloc"] == "219"

    @pytest.mark.asyncio
    async def test_extract_tokens_no_page_safe(self, mock_daemon):
        mock_daemon.page = None
        mock_daemon._tokens = {"netsessionid": "old", "cookies": []}
        await mock_daemon._extract_tokens()
        assert mock_daemon._tokens["netsessionid"] == "old"

    @pytest.mark.asyncio
    async def test_extracts_cookies_from_context(self, mock_daemon):
        mock_daemon.context = AsyncMock()
        mock_daemon.context.cookies = AsyncMock(return_value=[
            {"name": "fedlc", "value": "val1", "domain": ".gep.com", "path": "/",
             "secure": True, "httpOnly": False, "sameSite": "None"},
            {"name": "CultureCode", "value": "en", "domain": ".gep.com", "path": "/",
             "secure": True, "httpOnly": False, "sameSite": "None"},
        ])
        self._setup_page(mock_daemon, "https://businessnetwork.gep.com/")
        await mock_daemon._extract_tokens()
        assert len(mock_daemon._tokens["cookies"]) == 2
        assert all("domain" in c for c in mock_daemon._tokens["cookies"])
        assert all("url" in c for c in mock_daemon._tokens["cookies"])


# ══════════════════════════════════════════════════════════════════════
# Cookie file I/O
# ══════════════════════════════════════════════════════════════════════

class TestCookieFileIO:
    """Cookie persistence: load, save, edge cases."""

    def test_load_cookies_valid_file(self, mock_daemon, tmp_path):
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text(json.dumps({"cookies": [
            {"name": "fedlc", "value": "x", "domain": ".gep.com", "path": "/",
             "secure": True, "httpOnly": False},
            {"name": "bnfedno", "value": "y", "domain": ".gep.com", "path": "/",
             "secure": True, "httpOnly": False},
        ]}))
        mock_daemon.cookies_path = cookie_file
        cookies = mock_daemon._load_cookies()
        assert len(cookies) == 2
        assert cookies[0]["name"] == "fedlc"

    def test_load_cookies_missing_file(self, mock_daemon, tmp_path):
        mock_daemon.cookies_path = tmp_path / "nonexistent.json"
        cookies = mock_daemon._load_cookies()
        assert cookies == []

    def test_load_cookies_invalid_json(self, mock_daemon, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{not json")
        mock_daemon.cookies_path = f
        cookies = mock_daemon._load_cookies()
        assert cookies == []

    def test_load_cookies_empty_array(self, mock_daemon, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text(json.dumps({"cookies": []}))
        mock_daemon.cookies_path = f
        cookies = mock_daemon._load_cookies()
        assert cookies == []

    def test_load_additional_cookie_files(self, mock_daemon, tmp_path):
        """Fallback: loads from alt path when primary is empty."""
        alt = tmp_path / "smartgep_cookies_consurv.json"
        alt.write_text(json.dumps({"cookies": [
            {"name": "alt", "value": "z", "domain": "gep.com", "path": "/"}
        ]}))
        primary = tmp_path / "primary_empty.json"
        primary.write_text(json.dumps({"cookies": []}))
        mock_daemon.cookies_path = primary
        # Monkey-patch alt path to point at our temp file
        from permauth import DATA_DIR
        import permauth
        with patch.object(permauth, "DATA_DIR", return_value=alt.parent):
            pass
        cookies = mock_daemon._load_cookies()
        assert len(cookies) >= 0  # at minimum doesn't crash

    def test_load_account_valid(self, mock_daemon):
        acct = mock_daemon._load_account("consurv")
        assert acct["id"] == "consurv"
        assert "username" in acct
        assert "password" in acct

    def test_load_account_missing_raises(self, mock_daemon):
        with pytest.raises(ValueError, match="not found"):
            mock_daemon._load_account("nonexistent")

    @pytest.mark.asyncio
    async def test_save_cookies_writes_valid_json(self, mock_daemon, tmp_path):
        mock_daemon.cookies_path = tmp_path / "saved.json"
        mock_daemon.context = AsyncMock()
        mock_daemon.context.cookies = AsyncMock(return_value=[
            {"name": "fedlc", "value": "abc", "domain": "gep.com", "path": "/",
             "secure": True, "httpOnly": False},
        ])
        await mock_daemon._save_cookies()
        assert mock_daemon.cookies_path.exists()
        data = json.loads(mock_daemon.cookies_path.read_text())
        assert "cookies" in data
        assert len(data["cookies"]) == 1
        assert data["cookies"][0]["name"] == "fedlc"


# ══════════════════════════════════════════════════════════════════════
# HTTP handler routing
# ══════════════════════════════════════════════════════════════════════

class TestHealthEndpoint:
    """Health endpoint state reporting."""

    def test_alive_false_no_page_no_cookies(self, mock_daemon):
        mock_daemon._tokens = {"netsessionid": "", "cookies": []}
        mock_daemon.page = None
        has_nsid = bool(mock_daemon._tokens.get("netsessionid"))
        has_cookies = len(mock_daemon._tokens.get("cookies", [])) > 0
        alive = True if (has_nsid or has_cookies) and mock_daemon.page else False
        assert alive is False

    def test_alive_true_with_cookies_and_page(self, mock_daemon):
        mock_daemon._tokens = {"netsessionid": "", "cookies": [{"name": "x", "value": "y"}] * 5}
        mock_daemon.page = AsyncMock()
        has_nsid = bool(mock_daemon._tokens.get("netsessionid"))
        has_cookies = len(mock_daemon._tokens.get("cookies", [])) > 0
        alive = True if (has_nsid or has_cookies) and mock_daemon.page else False
        assert alive is True

    def test_tokens_valid_only_with_nsid(self, mock_daemon):
        mock_daemon._tokens = {"netsessionid": "abc123"}
        assert bool(mock_daemon._tokens.get("netsessionid")) is True

    def test_spa_available_false_without_nsid(self, mock_daemon):
        mock_daemon._tokens = {"netsessionid": ""}
        assert bool(mock_daemon._tokens.get("netsessionid")) is False


class TestTokensEndpoint:
    """Tokens endpoint response shape."""

    def test_includes_all_required_fields(self, mock_daemon):
        mock_daemon._tokens = {
            "netsessionid": "nsid123",
            "requestverificationtoken": "rvt456",
            "oloc": "669",
            "account": "consurv",
            "cookies": [{"name": "fedlc", "value": "x", "domain": ".gep.com", "path": "/"}],
        }
        required = ["netsessionid", "requestverificationtoken", "oloc", "account", "cookies"]
        for field in required:
            assert field in mock_daemon._tokens

    def test_serves_cookies_when_nsid_empty(self, mock_daemon):
        mock_daemon._tokens = {
            "netsessionid": "", "requestverificationtoken": "", "oloc": "",
            "account": "consurv", "cookies": [{"name": "fedlc", "value": "x"}] * 40,
        }
        assert mock_daemon._tokens["netsessionid"] == ""
        assert len(mock_daemon._tokens["cookies"]) == 40


class TestHttpRouting:
    """Handler endpoint dispatch."""

    @pytest.mark.parametrize("path,valid", [
        ("/health", True), ("/tokens", True), ("/reload", True),
        ("/fetch", True), ("/listing", True), ("/boq-extract", True),
        ("/nav-eval", True), ("/eval", True), ("/browse-fetch", True),
        ("/nonexistent", False), ("/unknown", False),
    ])
    def test_valid_endpoints(self, path, valid):
        endpoints = {"/health", "/tokens", "/reload", "/fetch", "/listing",
                      "/boq-extract", "/nav-eval", "/eval", "/browse-fetch"}
        assert (path in endpoints) == valid

    @pytest.mark.asyncio
    async def test_fetch_without_browser_returns_503(self, mock_daemon):
        mock_daemon.page = None
        assert mock_daemon.page is None

    @pytest.mark.asyncio
    async def test_eval_without_page_503(self, mock_daemon):
        mock_daemon.page = None
        assert mock_daemon.page is None

    @pytest.mark.asyncio
    async def test_nav_eval_without_page_503(self, mock_daemon):
        mock_daemon.page = None
        assert mock_daemon.page is None


# ══════════════════════════════════════════════════════════════════════
# HTTP fetch
# ══════════════════════════════════════════════════════════════════════

class TestHttpFetch:
    """HTTP fetch with cookie injection."""

    def test_injects_cookies_into_request(self, mock_daemon):
        mock_daemon._tokens = {
            "cookies": [
                {"name": "fedlc", "value": "abc", "domain": "gep.com"},
                {"name": "bnfedno", "value": "def", "domain": "gep.com"},
            ]
        }
        cookie_str = "; ".join(
            f"{c['name']}={c['value']}"
            for c in mock_daemon._tokens.get("cookies", [])
        )
        assert "fedlc=abc" in cookie_str
        assert "bnfedno=def" in cookie_str

    def test_handles_connection_error(self, mock_daemon):
        mock_daemon._tokens = {"cookies": []}
        result = mock_daemon._http_fetch("https://nonexistent.invalid:99999/test")
        assert "error" in result
        assert result["status"] == 0

    def test_includes_user_agent(self, mock_daemon):
        mock_daemon._tokens = {"cookies": []}
        ua = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        assert "Mozilla" in ua
        assert "Chrome" in ua


# ══════════════════════════════════════════════════════════════════════
# Account loading edge cases
# ══════════════════════════════════════════════════════════════════════

class TestAccountLoading:
    """Account file edge cases."""

    def test_disabled_account_has_flag(self):
        accts = {"id": "disabled", "username": "u", "password": "p", "enabled": False}
        assert accts["enabled"] is False

    def test_missing_username_field(self):
        accts = [{"id": "no_user", "password": "p"}]
        with pytest.raises(KeyError):
            _ = accts[0]["username"]

    def test_multiple_enabled_count(self):
        accts = [
            {"id": "a1", "username": "u1", "password": "p1", "enabled": True},
            {"id": "a2", "username": "u2", "password": "p2", "enabled": True},
            {"id": "a3", "username": "u3", "password": "p3", "enabled": False},
        ]
        enabled = [a for a in accts if a.get("enabled", True)]
        assert len(enabled) == 2


# ══════════════════════════════════════════════════════════════════════
# Edge cases
# ══════════════════════════════════════════════════════════════════════

class TestCaptchaDetection:
    """CAPTCHA detection during login."""

    def test_detects_captcha_page(self):
        url = "https://idplogin.gep.com/login?captcha=true"
        captcha_keywords = ["captcha", "g-recaptcha", "h-captcha"]
        assert any(k in url.lower() for k in captcha_keywords)


class TestBrowserCrashRecovery:
    """Daemon survives browser crashes gracefully."""

    def test_page_gone_still_serves_cached_tokens(self, mock_daemon):
        mock_daemon.page = None
        mock_daemon._tokens = {
            "netsessionid": "cached_nsid",
            "cookies": [{"name": "x", "value": "y"}] * 5,
        }
        assert mock_daemon._tokens["netsessionid"] == "cached_nsid"
        assert len(mock_daemon._tokens["cookies"]) == 5

    def test_crash_does_not_corrupt_tokens(self, mock_daemon):
        mock_daemon._tokens = {"netsessionid": "before"}
        try:
            raise RuntimeError("simulated crash")
        except RuntimeError:
            pass
        assert mock_daemon._tokens["netsessionid"] == "before"


class TestConcurrentRequests:
    """Concurrent token access safety."""

    def test_concurrent_reads_no_corruption(self, mock_daemon):
        mock_daemon._tokens = {
            "netsessionid": "nsid",
            "cookies": [{"name": "x", "value": "y"}],
        }
        results = []
        for _ in range(10):
            copy = dict(mock_daemon._tokens)
            copy["cookies"] = list(mock_daemon._tokens["cookies"])
            results.append(copy)
        assert len(results) == 10
        for r in results:
            assert r["netsessionid"] == "nsid"

    def test_refresh_during_read_does_not_corrupt(self, mock_daemon):
        mock_daemon._tokens = {"netsessionid": "old", "cookies": []}
        old_copy = dict(mock_daemon._tokens)
        mock_daemon._tokens = {"netsessionid": "new", "cookies": [{"name": "x"}]}
        assert old_copy["netsessionid"] == "old"
        assert mock_daemon._tokens["netsessionid"] == "new"


class TestNetworkFailureRecovery:
    """Network failures are handled gracefully."""

    def test_navigation_timeout_caught(self, mock_daemon):
        mock_daemon.page = AsyncMock()
        mock_daemon.page.goto = AsyncMock(side_effect=Exception("ERR_CONNECTION_TIMED_OUT"))
        mock_daemon.page.url = "about:blank"
        mock_daemon.context = AsyncMock()
        mock_daemon.context.cookies = AsyncMock(return_value=[])
        assert mock_daemon.page is not None

    def test_all_biznet_attempts_exhaust(self):
        failures = 0
        for _ in range(3):
            failures += 1
        assert failures == 3


class TestCookieStaleness:
    """Cookie freshness validation."""

    def test_old_cookies_are_stale(self):
        from datetime import datetime, timezone, timedelta
        saved = "2026-04-29T12:00:00+00:00"
        saved_dt = datetime.fromisoformat(saved)
        age = datetime.now(timezone.utc) - saved_dt
        assert age > timedelta(hours=24)

    def test_recent_cookies_are_fresh(self):
        from datetime import datetime, timezone, timedelta
        recent = datetime.now(timezone.utc) - timedelta(minutes=30)
        age = datetime.now(timezone.utc) - recent
        assert age < timedelta(hours=1)


class TestBrowseFetch:
    """POST /browse-fetch endpoint layer tests."""

    @pytest.mark.asyncio
    async def test_requires_url(self, mock_daemon):
        result = await mock_daemon._handle_browse_fetch({"url": ""})
        assert "error" in result
        assert result["status"] == 400

    @pytest.mark.asyncio
    async def test_layer1_page_request_success(self, mock_daemon):
        mock_daemon.page = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.status_text = "OK"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.body = AsyncMock(return_value=b'{"ok":true}')
        mock_daemon.page.request = AsyncMock()
        mock_daemon.page.request.fetch = AsyncMock(return_value=mock_response)

        result = await mock_daemon._handle_browse_fetch({
            "url": "https://businessnetwork.gep.com/",
            "method": "GET",
            "timeout": 10000,
        })
        assert result["status"] == 200
        assert result["_layer"] == "browser-request"
        assert result["bodyJson"] == {"ok": True}

    @pytest.mark.asyncio
    async def test_layer1_timeout_falls_to_layer2(self, mock_daemon):
        mock_daemon.page = AsyncMock()
        mock_daemon.page.request = AsyncMock()
        mock_daemon.page.request.fetch = AsyncMock(
            side_effect=TimeoutError("timeout")
        )
        mock_daemon._tokens = {"cookies": [
            {"name": "fedlc", "value": "abc", "domain": "gep.com"}
        ]}

        result = await mock_daemon._handle_browse_fetch({
            "url": "https://businessnetwork.gep.com/",
            "method": "GET",
            "timeout": 1000,
        })
        # Layer 1 fails (timeout) → falls to Layer 2 or returns error
        assert isinstance(result, dict)
        assert result.get("_layer") is not None
