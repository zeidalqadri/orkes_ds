"""Tests for ernie.theming — mood icons, status_line, alert_line format."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ernie.theming import (
    DOWN_CM,
    DOWN_ERNIE,
    FROWN,
    HAPPY_CM,
    HAPPY_ERNIE,
    SMILE,
    WARN_CM,
    WARN_ERNIE,
    alert_line,
    cm_icon,
    ernie_icon,
    status_line,
)


class TestCmIcon:
    def test_happy(self):
        assert cm_icon(alive=True, degraded=False) == HAPPY_CM

    def test_warn(self):
        assert cm_icon(alive=True, degraded=True) == WARN_CM

    def test_down(self):
        assert cm_icon(alive=False) == DOWN_CM

    def test_down_explicit(self):
        assert cm_icon(alive=False, degraded=False) == DOWN_CM


class TestErnieIcon:
    def test_happy(self):
        assert ernie_icon(alive=True, degraded=False) == HAPPY_ERNIE

    def test_warn(self):
        assert ernie_icon(alive=True, degraded=True) == WARN_ERNIE

    def test_down(self):
        assert ernie_icon(alive=False) == DOWN_ERNIE


class TestStatusLine:
    def test_all_ok_format(self):
        line = status_line(patrol_num=1, cm_alive=True, cm_degraded=False,
                           ernie_ok=True, drift_count=0, cm_cookies=42)
        assert HAPPY_CM in line
        assert HAPPY_ERNIE in line
        assert "patrol#1" in line
        assert "42cookies" in line
        assert "nodrift" in line
        assert SMILE in line

    def test_cm_down_format(self):
        line = status_line(patrol_num=5, cm_alive=False, cm_degraded=False,
                           ernie_ok=False, drift_count=0, cm_cookies=0)
        assert DOWN_CM in line
        assert "down" in line
        assert FROWN in line

    def test_drift_format(self):
        line = status_line(patrol_num=3, cm_alive=True, cm_degraded=False,
                           ernie_ok=False, drift_count=2, cm_cookies=10)
        assert "drift" in line
        assert "10cookies" in line
        assert FROWN in line

    def test_timestamp_present(self):
        line = status_line(patrol_num=1, cm_alive=True, cm_degraded=False,
                           ernie_ok=True, drift_count=0)
        assert "[" in line and "]" in line

    def test_no_cookies_omitted(self):
        line = status_line(patrol_num=1, cm_alive=True, cm_degraded=False,
                           ernie_ok=True, drift_count=0, cm_cookies=0)
        assert "0cookies" not in line


class TestAlertLine:
    def test_alert_format(self):
        line = alert_line("Cookie Monster down: timeout")
        assert DOWN_CM in line
        assert DOWN_ERNIE in line
        assert "ALERT" in line
        assert "Cookie Monster down: timeout" in line

    def test_recovery_format(self):
        line = alert_line("All checks passed", is_recovery=True)
        assert HAPPY_CM in line
        assert HAPPY_ERNIE in line
        assert "RECOVERY" in line
        assert "All checks passed" in line
