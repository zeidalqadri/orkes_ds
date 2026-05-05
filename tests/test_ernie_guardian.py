"""Tests for ernie.guardian — health probes and patrol cycle."""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ernie.drift_detect import fingerprint_page
from ernie.guardian import (
    _load_state,
    _save_state,
    probe_cookie_monster,
    probe_url,
    run_check,
)


class FakeHTTPResponse:
    def __init__(self, status=200, headers=None, body=b"{}"):
        self.status = status
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeURLError(Exception):
    def __init__(self, reason="", code=0):
        self.reason = reason
        self.code = code
        super().__init__(str(reason))


class TestProbeCookieMonster:
    @patch("ernie.guardian.urlopen")
    def test_alive(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(
            body=json.dumps({"alive": True, "account": "consurv", "cookies_count": 42}).encode()
        )
        result = probe_cookie_monster(port=9876)
        assert result["alive"] is True
        assert result["account"] == "consurv"
        assert result["cookies_count"] == 42

    @patch("ernie.guardian.urlopen")
    def test_down(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")
        result = probe_cookie_monster(port=9876)
        assert result["alive"] is False
        assert "error" in result

    @patch("ernie.guardian.urlopen")
    def test_bad_json(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(body=b"not json")
        result = probe_cookie_monster(port=9876)
        assert result["alive"] is True


class TestProbeUrl:
    @patch("ernie.guardian.urlopen")
    def test_reachable(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(
            status=200,
            body=b"<html><body>BizNet Login</body></html>",
        )
        result = probe_url("https://businessnetwork.gep.com/")
        assert result["reachable"] is True
        assert result["status"] == 200
        assert "BizNet" in result["snippet"]

    @patch("ernie.guardian.urlopen")
    def test_unreachable(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("DNS resolution failed")
        result = probe_url("https://invalid.example.com/")
        assert result["reachable"] is False
        assert "error" in result


class TestRunCheck:
    @patch("ernie.guardian.probe_cookie_monster")
    @patch("ernie.guardian.probe_url")
    @patch("ernie.guardian.fingerprint_page")
    @patch("ernie.guardian.detect_drift")
    @patch("ernie.guardian.detect_auth_drift")
    @patch("ernie.guardian.fingerprint_auth_probe")
    def test_all_ok(
        self, mock_auth_fp, mock_auth_drift,
        mock_drift, mock_fp, mock_probe_url, mock_cm
    ):
        mock_cm.return_value = {"alive": True, "cookies_count": 42}
        mock_probe_url.return_value = {
            "reachable": True, "status": 200,
            "snippet": "<html>ok</html>", "url": "https://businessnetwork.gep.com/",
        }
        mock_fp.return_value = fingerprint_page("BizNet", "https://businessnetwork.gep.com/", "<html>ok</html>")
        mock_drift.return_value = []
        mock_auth_fp.return_value = {"composite_hash": "aaa", "probes": {}, "timestamp": time.time()}
        mock_auth_drift.return_value = []

        result = run_check(port=9876)
        assert result["ok"] is True
        assert result["alerts"] == []
        assert "cookie_monster" in result
        assert "biznet" in result
        assert "fingerprint" in result
        assert "auth_fingerprint" in result
        assert "drifts" in result
        assert "auth_drifts" in result

    @patch("ernie.guardian.probe_cookie_monster")
    @patch("ernie.guardian.probe_url")
    @patch("ernie.guardian.fingerprint_page")
    @patch("ernie.guardian.detect_drift")
    @patch("ernie.guardian.detect_auth_drift")
    @patch("ernie.guardian.fingerprint_auth_probe")
    def test_cm_down(
        self, mock_auth_fp, mock_auth_drift,
        mock_drift, mock_fp, mock_probe_url, mock_cm
    ):
        mock_cm.return_value = {"alive": False, "error": "Connection refused"}
        mock_probe_url.return_value = {
            "reachable": True, "status": 200, "snippet": "", "url": "",
        }
        mock_fp.return_value = fingerprint_page("BizNet", "", "")
        mock_drift.return_value = []
        mock_auth_fp.return_value = {"composite_hash": "aaa", "probes": {}, "timestamp": time.time()}
        mock_auth_drift.return_value = []

        result = run_check(port=9876)
        assert result["ok"] is False
        assert any("Cookie Monster down" in a for a in result["alerts"])


class TestStatePersistence:
    def test_load_empty_returns_defaults(self, tmp_path):
        with patch("ernie.guardian.GUARDIAN_STATE_FILE", tmp_path / "nonexistent.json"):
            state = _load_state()
            assert state["down_since"] is None
            assert state["drift_since"] is None
            assert state["total_checks"] == 0

    def test_save_and_load(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch("ernie.guardian.GUARDIAN_STATE_FILE", state_file):
            _save_state({"total_checks": 42, "down_since": None, "drift_since": None, "total_alerts": 1})
            loaded = _load_state()
            assert loaded["total_checks"] == 42
            assert loaded["total_alerts"] == 1

    def test_load_corrupted_returns_defaults(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("{corrupted json")
        with patch("ernie.guardian.GUARDIAN_STATE_FILE", state_file):
            state = _load_state()
            assert state["total_checks"] == 0
