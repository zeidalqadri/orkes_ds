"""Tests for ernie.drift_detect — page fingerprinting and profile drift detection."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ernie.drift_detect import (
    detect_drift,
    fingerprint_json_response,
    fingerprint_page,
    init_profile,
    load_profile,
    save_profile,
)

SAMPLE_HTML = """<html><body><form action="/Account/Login">
<input name="Username" placeholder="Username" />
<input name="Password" type="password" />
<button type="submit">Sign In</button>
</form></body></html>"""


class TestFingerprintPage:
    def test_basic_structure(self):
        fp = fingerprint_page(
            title="BizNet",
            url="https://idplogin.gep.com/Account/Login?return=1",
            html_snippet=SAMPLE_HTML,
        )
        assert fp["title"] == "BizNet"
        assert "idplogin.gep.com" in fp["url_domain"]
        assert fp["login_host_match"] is True
        assert fp["selector_count"] > 0
        assert fp["selector_count"] > 0
        assert fp["html_length"] == len(SAMPLE_HTML)
        assert len(fp["html_prefix_hash"]) == 16

    def test_biznet_match(self):
        fp = fingerprint_page(title="BizNet", url="https://businessnetwork.gep.com/")
        assert fp["biznet_match"] is True
        assert fp["login_host_match"] is False

    def test_url_path_extracted(self):
        fp = fingerprint_page(title="", url="https://example.com/Account/Login?x=1#section")
        assert "/Account/Login" in fp["url_path"]
        assert "section" in fp["url_fragment"]

    def test_empty_snippet(self):
        fp = fingerprint_page(title="", url="https://example.com/", html_snippet="")
        assert fp["html_length"] == 0
        assert fp["html_prefix_hash"] == ""


class TestProfileSaveLoad:
    def test_roundtrip(self, tmp_path):
        from ernie import drift_detect as dd
        original = dd.PROFILES_DIR
        try:
            dd.PROFILES_DIR = tmp_path
            fp = fingerprint_page("Test", "https://example.com/", "hello")
            save_profile("test_page", fp)
            loaded = load_profile("test_page")
            assert loaded is not None
            assert loaded["title"] == "Test"
            assert loaded["url_domain"] == "example.com"
        finally:
            dd.PROFILES_DIR = original

    def test_load_nonexistent(self):
        assert load_profile("nonexistent_12345") is None


class TestInitProfile:
    def test_creates_new(self, tmp_path):
        from ernie import drift_detect as dd
        original = dd.PROFILES_DIR
        try:
            dd.PROFILES_DIR = tmp_path
            profile = init_profile("new_page")
            assert profile["name"] == "new_page"
            assert profile["fingerprint"] is None
        finally:
            dd.PROFILES_DIR = original

    def test_returns_existing(self, tmp_path):
        from ernie import drift_detect as dd
        original = dd.PROFILES_DIR
        try:
            dd.PROFILES_DIR = tmp_path
            from ernie.drift_detect import save_profile
            fp = fingerprint_page("Existing", "https://example.com/")
            save_profile("existing_page", {"name": "existing_page", "fingerprint": fp})
            profile = init_profile("existing_page")
            assert profile["fingerprint"] is not None
            assert profile["fingerprint"]["title"] == "Existing"
        finally:
            dd.PROFILES_DIR = original


class TestDetectDrift:
    def test_first_run_no_drift(self, tmp_path):
        from ernie import drift_detect as dd
        original = dd.PROFILES_DIR
        try:
            dd.PROFILES_DIR = tmp_path
            fp = fingerprint_page("BizNet", "https://businessnetwork.gep.com/", SAMPLE_HTML)
            drifts = detect_drift("login_test", fp)
            assert drifts == []
        finally:
            dd.PROFILES_DIR = original

    def test_detects_domain_change(self, tmp_path):
        from ernie import drift_detect as dd
        original = dd.PROFILES_DIR
        try:
            dd.PROFILES_DIR = tmp_path
            fp1 = fingerprint_page("BizNet", "https://businessnetwork.gep.com/", SAMPLE_HTML)
            detect_drift("domain_test", fp1)  # establishes baseline
            fp2 = fingerprint_page("BizNet", "https://evil.gep.com/", SAMPLE_HTML)
            drifts = detect_drift("domain_test", fp2)
            assert any("domain" in d for d in drifts)
        finally:
            dd.PROFILES_DIR = original

    def test_detects_html_change(self, tmp_path):
        from ernie import drift_detect as dd
        original = dd.PROFILES_DIR
        try:
            dd.PROFILES_DIR = tmp_path
            fp1 = fingerprint_page("BizNet", "https://businessnetwork.gep.com/", "<html>original</html>")
            detect_drift("html_test", fp1)
            fp2 = fingerprint_page("BizNet", "https://businessnetwork.gep.com/", "<html>modified</html>")
            drifts = detect_drift("html_test", fp2)
            assert any("HTML" in d for d in drifts)
        finally:
            dd.PROFILES_DIR = original

    def test_no_drift_when_unchanged(self, tmp_path):
        from ernie import drift_detect as dd
        original = dd.PROFILES_DIR
        try:
            dd.PROFILES_DIR = tmp_path
            fp = fingerprint_page("BizNet", "https://businessnetwork.gep.com/", SAMPLE_HTML)
            detect_drift("stable_test", fp)
            drifts = detect_drift("stable_test", fp)
            assert drifts == []
        finally:
            dd.PROFILES_DIR = original

    def test_detects_login_host_match_change(self, tmp_path):
        from ernie import drift_detect as dd
        original = dd.PROFILES_DIR
        try:
            dd.PROFILES_DIR = tmp_path
            fp1 = fingerprint_page("BizNet", "https://businessnetwork.gep.com/")
            detect_drift("login_host_test", fp1)
            fp2 = fingerprint_page("BizNet", "https://idplogin.gep.com/Account/Login")
            drifts = detect_drift("login_host_test", fp2)
            assert any("login_host_match" in d for d in drifts)
        finally:
            dd.PROFILES_DIR = original


class TestFingerprintJsonResponse:
    def test_dict_shape(self):
        data = {"name": "John", "age": 30, "items": [1, 2, 3]}
        fp = fingerprint_json_response(data)
        assert "name" in fp["top_keys"]
        assert "shape" in fp
        assert "timestamp" in fp

    def test_list_shape(self):
        data = [{"a": 1, "b": "x"}]
        fp = fingerprint_json_response(data)
        assert "list<" in fp["shape"]

    def test_nested_dict(self):
        data = {"a": {"b": {"c": [1, 2]}}}
        fp = fingerprint_json_response(data)
        assert "shape" in fp
