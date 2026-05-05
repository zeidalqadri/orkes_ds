"""Tests for ernie.response_shape — auth flow fingerprinting and drift detection."""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ernie.response_shape import (
    AUTH_PROBE_URLS,
    _composite_hash,
    detect_auth_drift,
    extract_body_markers,
    fingerprint_auth_probe,
    fingerprint_redirect_chain,
    load_auth_profile,
    save_auth_profile,
)

SAMPLE_LOGIN_HTML = """
<html><body>
<form action="/Account/Login" method="post">
<input name="Username" type="text" />
<input name="Password" type="password" />
<input name="__RequestVerificationToken" type="hidden" />
<button type="submit">Sign In</button>
</form>
<a href="/forgotpassword">Forgot Password</a>
</body></html>
"""


class TestExtractBodyMarkers:
    def test_login_form_detected(self):
        m = extract_body_markers(SAMPLE_LOGIN_HTML)
        assert m["has_login_form"] is True
        assert m["has_password_field"] is True
        assert m["has_username_field"] is True
        assert m["sign_in_button"] is True
        assert m["has_csrf_token"] is True
        assert m["has_forgot_password"] is True
        assert "Username" in m["field_names"]
        assert "Password" in m["field_names"]

    def test_no_form(self):
        m = extract_body_markers("<html><body>Hello</body></html>")
        assert m["has_login_form"] is False
        assert m["has_password_field"] is False
        assert m.get("field_names", []) == []

    def test_error_detected(self):
        m = extract_body_markers('<div class="alert alert-danger">Invalid credentials</div>')
        assert m["has_error"] is True

    def test_captcha_detected(self):
        m = extract_body_markers('<div class="g-recaptcha"></div>')
        assert m["has_captcha"] is True

    def test_form_actions_extracted(self):
        m = extract_body_markers(SAMPLE_LOGIN_HTML)
        assert "/Account/Login" in m["form_actions"]


class FakeURLResponse:
    """Simulate urllib response for redirect chain tests."""
    def __init__(self, status=200, headers=None, body=b""):
        self.status = status
        self.headers = {"Location": "", "Content-Type": "text/html"}
        if headers:
            self.headers.update(headers)
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TestFingerprintRedirectChain:
    @patch("ernie.response_shape.urlopen")
    def test_single_hop_ok(self, mock_urlopen):
        mock_urlopen.return_value = FakeURLResponse(
            status=200,
            headers={"Content-Type": "text/html", "Set-Cookie": "sess=abc"},
            body=b"<html>ok</html>",
        )
        fp = fingerprint_redirect_chain("https://example.com/login")
        assert fp["hop_count"] == 1
        assert fp["final_status"] == 200
        assert fp["body_length"] > 0
        assert fp["final_url"] == "https://example.com/login"
        assert len(fp["body_hash"]) == 16

    @patch("ernie.response_shape.urlopen")
    def test_redirect_chain(self, mock_urlopen):
        mock_urlopen.side_effect = [
            FakeURLResponse(status=302, headers={"Location": "https://idp.example.com/login"}),
            FakeURLResponse(status=200, headers={}, body=b"<html>login page</html>"),
        ]
        fp = fingerprint_redirect_chain("https://example.com/login")
        assert fp["hop_count"] == 2
        assert fp["final_status"] == 200
        assert "idp.example.com" in fp["final_url"]

    def test_body_markers_in_result(self):
        mock_resp = FakeURLResponse(
            status=200, body=SAMPLE_LOGIN_HTML.encode()
        )
        with patch("ernie.response_shape.urlopen", return_value=mock_resp):
            fp = fingerprint_redirect_chain("https://example.com/login")
        assert fp["body_markers"]["has_login_form"] is True
        assert fp["body_markers"]["has_password_field"] is True


class TestCompositeHash:
    def test_stable_for_same_input(self):
        probes_a = {
            "https://example.com": {
                "hop_count": 2, "final_status": 200,
                "body_markers": {"has_login_form": True, "has_password_field": True,
                                 "has_captcha": False, "has_error": False},
                "body_hash": "abc123", "hops": [
                    {"status": 302, "headers": {"location": "https://idp.example.com"}},
                    {"status": 200, "headers": {}},
                ],
            }
        }
        probes_b = json.loads(json.dumps(probes_a))
        assert _composite_hash(probes_a) == _composite_hash(probes_b)

    def test_changes_on_different_input(self):
        probes_a = {"https://example.com": {"hop_count": 2, "final_status": 200,
                    "body_markers": {}, "body_hash": "abc", "hops": [{"status": 302, "headers": {}}]}}
        probes_b = {"https://example.com": {"hop_count": 3, "final_status": 200,
                    "body_markers": {}, "body_hash": "abc", "hops": [{"status": 302, "headers": {}}]}}
        assert _composite_hash(probes_a) != _composite_hash(probes_b)


class TestFingerprintAuthProbe:
    @patch("ernie.response_shape.urlopen")
    def test_includes_all_urls(self, mock_urlopen):
        mock_urlopen.return_value = FakeURLResponse(status=200, body=b"ok")
        result = fingerprint_auth_probe(timeout=5)
        assert "probes" in result
        for url in AUTH_PROBE_URLS:
            assert url in result["probes"]
        assert "composite_hash" in result
        assert len(result["composite_hash"]) == 32


class TestDetectAuthDrift:
    def _make_profile(self, overrides=None):
        base = {
            "probes": {
                url: {
                    "hop_count": 2, "final_status": 200,
                    "body_markers": {"has_login_form": True, "has_password_field": True,
                                     "has_username_field": True, "has_captcha": False,
                                     "login_with_password": True, "sign_in_button": True,
                                     "has_error": False, "field_names": ["Username", "Password"],
                                     "form_actions": ["/Account/Login"]},
                    "body_hash": "abc", "hops": [{"status": 302, "headers": {"location": "https://idp.gep.com"}},
                                                  {"status": 200, "headers": {}}],
                }
                for url in AUTH_PROBE_URLS
            },
            "composite_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        }
        base["composite_hash"] = _composite_hash(base["probes"])
        if overrides:
            for k, v in overrides.items():
                if k == "probes":
                    for url, val in v.items():
                        base["probes"][url].update(val)
        return base

    @patch("ernie.response_shape.save_auth_profile")
    @patch("ernie.response_shape.load_auth_profile")
    def test_first_run_no_drift(self, mock_load, mock_save):
        mock_load.return_value = None
        current = self._make_profile()
        drifts = detect_auth_drift(current)
        assert drifts == []
        mock_save.assert_called_once()

    @patch("ernie.response_shape.save_auth_profile")
    @patch("ernie.response_shape.load_auth_profile")
    def test_detects_composite_hash_change(self, mock_load, mock_save):
        mock_load.return_value = {
            "name": "auth_flow", "created": time.time(),
            "fingerprint": self._make_profile({"probes": {AUTH_PROBE_URLS[0]: {"hop_count": 1,
                        "final_status": 301, "body_markers": {}, "body_hash": "", "hops": []}}}),
        }
        # Different hash
        current = self._make_profile()
        drifts = detect_auth_drift(current)
        assert len(drifts) >= 1

    @patch("ernie.response_shape.save_auth_profile")
    @patch("ernie.response_shape.load_auth_profile")
    def test_detects_hop_count_change(self, mock_load, mock_save):
        baseline = self._make_profile()
        current = self._make_profile({"probes": {AUTH_PROBE_URLS[0]: {"hop_count": 5}}})
        mock_load.return_value = {"name": "auth_flow", "created": time.time(), "fingerprint": baseline}
        drifts = detect_auth_drift(current)
        assert any("hop count" in d for d in drifts)


class TestSaveLoadAuthProfile:
    def test_roundtrip(self, tmp_path):
        from ernie.response_shape import PROFILES_DIR
        original = PROFILES_DIR
        try:
            from ernie import response_shape as rs
            rs.PROFILES_DIR = tmp_path
            fp = {"composite_hash": "test", "probes": {}, "timestamp": time.time()}
            save_auth_profile("test_flow", {"name": "test_flow", "fingerprint": fp})
            loaded = load_auth_profile("test_flow")
            assert loaded is not None
            assert loaded["fingerprint"]["composite_hash"] == "test"
        finally:
            rs.PROFILES_DIR = original
