"""Reusable panel components — header bars, summary strips, status badges, cell formatters."""

from datetime import datetime, timezone
from rich.panel import Panel
from rich.text import Text

from .theme import STATUS_STYLE_MAP, PLATFORM_STYLE_MAP, PHASE_STYLE_MAP


def header_bar(title: str, version: str | None = None) -> Panel:
    t = Text()
    t.append(f" {title.upper()} ", style="bold bright_white on blue")
    if version:
        t.append(f"  v{version}", style="dim cyan")
    t.append(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", style="dim white")
    return Panel(t, style="blue", expand=True, padding=(0, 1))


def summary_bar(label: str, total: int, filtered: int | None = None,
                limit: int | None = None, offset: int | None = None,
                query_ms: float | None = None) -> Text:
    t = Text()
    t.append(f" {label.upper()} ", style="bold bright_white on bright_black")
    t.append(f"  {total}", style="summary.count")
    t.append(" total", style="summary.label")

    if filtered is not None and filtered != total:
        t.append(f"  {filtered}", style="summary.count")
        t.append(" matched", style="summary.label")

    if limit is not None and offset is not None:
        eff_total = total if filtered is None else filtered
        start = offset + 1
        end = min(offset + limit, eff_total)
        if offset > 0 or end < eff_total:
            t.append(f"  showing {start}-{end}", style="summary.label")

    if query_ms is not None:
        t.append(f"  [{query_ms:.0f}ms]", style="summary.timing")

    return t


def status_badge(status: str) -> Text:
    key = status.lower().replace(" ", "_")
    style = STATUS_STYLE_MAP.get(key, "white")
    return Text(status.upper(), style=style)


def platform_badge(platform: str) -> Text:
    key = platform.lower().replace(" ", "")
    style = PLATFORM_STYLE_MAP.get(key, "entity")
    return Text(platform, style=style)


def phase_badge(phase: str) -> Text:
    """Workflow phase badge (pricing/approval/packaging/submitted/post_submit)."""
    if not phase:
        return Text("—", style="muted")
    key = phase.lower().replace(" ", "_")
    style = PHASE_STYLE_MAP.get(key, "dim white")
    return Text(phase.upper(), style=style)


def entity_badge(slug: str) -> Text:
    """Short entity slug display. Maps slug to shortcode."""
    if not slug:
        return Text("—", style="muted")
    short = _entity_short(slug)
    return Text(short, style="entity.slug")


def _entity_short(slug: str) -> str:
    """consurv-technic → CT, dyna-om → DO, dyna-segmen → DS, dyna-sche → DSC"""
    shorts = {
        "consurv-technic": "CT",
        "dyna-om": "DO",
        "dyna-segmen": "DS",
        "dyna-sche": "DSC",
    }
    return shorts.get(slug, slug[:6].upper())


def deadline_cell(deadline_str: str | None, wide: bool = False) -> Text:
    if not deadline_str:
        return Text("—", style="muted")

    try:
        dl = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return Text(deadline_str[:10], style="date")

    now = datetime.now(timezone.utc)
    delta = dl - now
    hours = delta.total_seconds() / 3600

    if hours < 0:
        label = _relative_past(delta)
        style = "date.past"
    elif hours < 24:
        label = f"{max(1, int(hours))}h left"
        style = "date.urgent"
    elif hours < 72:
        label = f"{int(hours / 24)}d{int(hours % 24)}h"
        style = "date.soon"
    else:
        label = dl.strftime("%d %b")
        style = "date.safe"

    if wide:
        return Text(f"{label:<7s} {dl.strftime('%d/%m %H:%M')}", style=style)
    return Text(label, style=style)


def _relative_past(delta) -> str:
    hours = abs(delta.total_seconds()) / 3600
    if hours < 24:
        return f"{int(hours)}h ago"
    days = int(hours / 24)
    if days < 30:
        return f"{days}d ago"
    return f"{int(days / 30)}mo ago"


def amount_cell(amount: float | None, currency: str = "RM") -> Text:
    if amount is None or amount == 0:
        return Text("—", style="amount.zero")
    formatted = f"{currency} {amount:,.2f}"
    return Text(formatted, style="amount")


def levers_cell(levers: dict | None) -> Text:
    """Compact margin levers display: M15 O8 C3 R0"""
    if not levers:
        return Text("—", style="muted")
    t = Text()
    m = levers.get("markup", 0)
    o = levers.get("overhead", 0)
    c = levers.get("contingency", 0)
    r = levers.get("risk_premium", 0)
    t.append(f"M{m:g}", style="lever.markup")
    t.append(" ", style="dim")
    t.append(f"O{o:g}", style="lever.overhead")
    t.append(" ", style="dim")
    t.append(f"C{c:g}", style="lever.contingency")
    if r > 0:
        t.append(" ", style="dim")
        t.append(f"R{r:g}", style="lever.risk")
    return t


def notification_cell(channel: str | int | None) -> Text:
    if channel:
        return Text(str(channel), style="bright_cyan")
    return Text("—", style="muted")

