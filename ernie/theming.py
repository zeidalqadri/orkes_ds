"""Themed log indicators for Cookie Monster and Ernie.

Every log line during patrol cycles gets a mood indicator:
  Happy:  🍪🐻  (all good)
  Warning: 🍪😟 or 🐻😟
  Down:   🍪💀 or 🐻💀
"""
from datetime import UTC, datetime

HAPPY_CM = "\U0001f36a"       # 🍪
HAPPY_ERNIE = "\U0001f43b"    # 🐻
WARN_CM = "\U0001f36a\U0001f61f"   # 🍪😟
WARN_ERNIE = "\U0001f43b\U0001f61f" # 🐻😟
DOWN_CM = "\U0001f36a\U0001f480"    # 🍪💀
DOWN_ERNIE = "\U0001f43b\U0001f480" # 🐻💀
SMILE = "\U0001f604"  # 😄
FROWN = "\U0001f61e"  # 😞


def cm_icon(alive: bool, degraded: bool = False) -> str:
    if alive and not degraded:
        return HAPPY_CM
    elif alive and degraded:
        return WARN_CM
    return DOWN_CM


def ernie_icon(alive: bool, degraded: bool = False) -> str:
    if alive and not degraded:
        return HAPPY_ERNIE
    elif alive and degraded:
        return WARN_ERNIE
    return DOWN_ERNIE


def status_line(
    patrol_num: int,
    cm_alive: bool,
    cm_degraded: bool,
    ernie_ok: bool,
    drift_count: int,
    cm_cookies: int = 0,
) -> str:
    ci = cm_icon(cm_alive, cm_degraded)
    ei = ernie_icon(ernie_ok, drift_count > 0)
    mood = SMILE if (cm_alive and ernie_ok and drift_count == 0) else FROWN
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    tokens = f"{cm_cookies}cookies" if cm_cookies else ""
    dr = f"{drift_count}drift" if drift_count else "nodrift"
    return (
        f"[{ts}] [{ei}\U0000fe0fErnie] patrol#{patrol_num} "
        f"\u2014 CookieMonster{ci}:{'alive' if cm_alive else 'down'}({tokens}) "
        f"| drift:{dr} | {mood}"
    )


def alert_line(msg: str, is_recovery: bool = False) -> str:
    icon = HAPPY_CM + HAPPY_ERNIE if is_recovery else DOWN_CM + DOWN_ERNIE
    prefix = "\u2705RECOVERY" if is_recovery else "\u26a0\ufe0fALERT"
    return f"{icon} {prefix}: {msg}"
