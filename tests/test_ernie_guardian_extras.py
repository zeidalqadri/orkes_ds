"""Extended tests for ernie.guardian — patrol output format, state transitions,
alert/recovery markers, and section formatting."""
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ernie.drift_detect import fingerprint_page
from ernie.guardian import (
    _load_state,
    _save_state,
    patrol_section,
    run_check,
)


class TestPatrolSection:
    def test_ok_format(self):
        line = patrol_section("Cookie Monster health", True, "42 cookies")
        assert "[OK]" in line
        assert "\u2705" in line  # ✅
        assert "Cookie Monster health" in line
        assert "42 cookies" in line

    def test_fail_format(self):
        line = patrol_section("BizNet reachability", False, "Connection refused")
        assert "[FAIL]" in line
        assert "\u274c" in line  # ❌
        assert "Connection refused" in line

    def test_no_detail(self):
        line = patrol_section("Test", True)
        assert "[OK]" in line
        assert "Test" in line
        # Should not have a trailing "—"
        assert line.strip().endswith("✅ Test")

    def test_empty_detail(self):
        line = patrol_section("Test", False, "")
        assert "[FAIL]" in line

    def test_drift_detail(self):
        line = patrol_section("Page drift", False, "2 drift(s)")
        assert "[FAIL]" in line
        assert "2 drift(s)" in line


class TestRunCheckExtended:
    @patch("ernie.guardian.probe_cookie_monster")
    @patch("ernie.guardian.probe_url")
    @patch("ernie.guardian.fingerprint_page")
    @patch("ernie.guardian.detect_drift")
    @patch("ernie.guardian.detect_auth_drift")
    @patch("ernie.guardian.fingerprint_auth_probe")
    def test_alerts_collected_on_biznet_down(
        self, mock_auth_fp, mock_auth_drift, mock_drift,
        mock_fp, mock_probe_url, mock_cm
    ):
        mock_cm.return_value = {"alive": True, "cookies_count": 42}
        mock_probe_url.return_value = {
            "reachable": False, "status": 0,
            "snippet": "", "url": "https://businessnetwork.gep.com/",
            "error": "DNS failure",
        }
        mock_fp.return_value = fingerprint_page("BizNet", "", "")
        mock_drift.return_value = []
        mock_auth_fp.return_value = {"composite_hash": "aaa", "probes": {}, "timestamp": time.time()}
        mock_auth_drift.return_value = []

        result = run_check(port=9876)
        assert any("BizNet unreachable" in a for a in result["alerts"])

    @patch("ernie.guardian.probe_cookie_monster")
    @patch("ernie.guardian.probe_url")
    @patch("ernie.guardian.fingerprint_page")
    @patch("ernie.guardian.detect_drift")
    @patch("ernie.guardian.detect_auth_drift")
    @patch("ernie.guardian.fingerprint_auth_probe")
    def test_alerts_on_drift_and_auth_drift(
        self, mock_auth_fp, mock_auth_drift, mock_drift,
        mock_fp, mock_probe_url, mock_cm
    ):
        mock_cm.return_value = {"alive": True, "cookies_count": 42}
        mock_probe_url.return_value = {
            "reachable": True, "status": 200,
            "snippet": "<html>new page</html>",
            "url": "https://businessnetwork.gep.com/",
        }
        mock_fp.return_value = fingerprint_page("BizNet", "https://businessnetwork.gep.com/", "<html>new page</html>")
        mock_drift.return_value = ["domain changed"]
        mock_auth_fp.return_value = {"composite_hash": "bbb", "probes": {}, "timestamp": time.time()}
        mock_auth_drift.return_value = ["Auth flow composite hash changed"]

        result = run_check(port=9876)
        assert result["ok"] is False
        drift_alerts = [a for a in result["alerts"] if "Drift" in a or "Auth flow" in a]
        assert len(drift_alerts) >= 1
        assert "domain changed" in result["drifts"]
        assert "Auth flow composite hash changed" in result["auth_drifts"]

    def test_full_return_structure(self):
        """Verify run_check returns all expected keys."""
        with patch("ernie.guardian.probe_cookie_monster") as mock_cm, \
             patch("ernie.guardian.probe_url") as mock_url, \
             patch("ernie.guardian.fingerprint_page") as mock_fp, \
             patch("ernie.guardian.detect_drift") as mock_dd, \
             patch("ernie.guardian.fingerprint_auth_probe") as mock_afp, \
             patch("ernie.guardian.detect_auth_drift") as mock_ad:
            mock_cm.return_value = {"alive": True, "cookies_count": 42}
            mock_url.return_value = {"reachable": True, "status": 200, "snippet": "", "url": ""}
            mock_fp.return_value = fingerprint_page("BizNet", "", "")
            mock_dd.return_value = []
            mock_afp.return_value = {"composite_hash": "aaa", "probes": {}, "timestamp": time.time()}
            mock_ad.return_value = []

            result = run_check(port=9876)
            expected_keys = {"timestamp", "ok", "alerts", "cookie_monster",
                             "biznet", "fingerprint", "drifts",
                             "auth_fingerprint", "auth_drifts"}
            assert expected_keys.issubset(result.keys())
            assert isinstance(result["timestamp"], str)
            assert isinstance(result["alerts"], list)
            assert "T" in result["timestamp"]  # ISO format


class TestStateTransitions:
    def test_state_file_created_on_save(self, tmp_path):
        state_file = tmp_path / "er_state.json"
        with patch("ernie.guardian.GUARDIAN_STATE_FILE", state_file):
            _save_state({"total_checks": 1, "down_since": None, "drift_since": None, "total_alerts": 0})
            assert state_file.exists()
            assert state_file.stat().st_mode & 0o600  # readable by owner

    def test_alerts_counter_increments(self, tmp_path):
        state_file = tmp_path / "er_state2.json"
        with patch("ernie.guardian.GUARDIAN_STATE_FILE", state_file):
            _save_state({"total_checks": 5, "down_since": None, "drift_since": None, "total_alerts": 3})
            loaded = _load_state()
            assert loaded["total_alerts"] == 3
            assert loaded["total_checks"] == 5
