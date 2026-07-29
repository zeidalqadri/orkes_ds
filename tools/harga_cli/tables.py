"""Rich table builders for tenders, bids, entities, and status dashboard."""

import shutil

from rich.table import Table
from rich.text import Text

from .theme import console, STATUS_STYLE_MAP
from .panels import (
    status_badge, platform_badge, phase_badge, entity_badge,
    deadline_cell, amount_cell, levers_cell, notification_cell, summary_bar,
)


def _term_wide() -> bool:
    return shutil.get_terminal_size().columns >= 120


def render_tenders(data: dict, con=None) -> None:
    """Render tenders list. v9 schema.

    Expected shape:
        {"tenders": [...], "total": int, "limit": int, "offset": int}
    Each tender: {id, title, portal, reference, status, deadline, amount, issuer}
    """
    c = con or console
    tenders = data.get("tenders", [])
    wide = _term_wide()

    table = Table(
        show_header=True, header_style="header", show_lines=False,
        pad_edge=False, padding=(0, 1), expand=True,
        row_styles=["", "on #111111"],
    )

    table.add_column("REF", style="reference", no_wrap=True)
    table.add_column("TITLE", style="title", ratio=1, no_wrap=True, overflow="ellipsis")
    if wide:
        table.add_column("SRC", no_wrap=True)
    table.add_column("STATUS", no_wrap=True, justify="center")
    table.add_column("DUE", no_wrap=True)
    table.add_column("AMOUNT", no_wrap=True, justify="right")
    if wide:
        table.add_column("ISSUER", style="dim", no_wrap=True, overflow="ellipsis")

    for t in tenders:
        ref = t.get("reference") or t.get("id", "")
        row = [
            str(ref),
            _truncate(t.get("title", ""), 50 if wide else 28),
        ]
        if wide:
            row.append(platform_badge(t.get("portal") or t.get("entity", "")))
        row += [
            status_badge(t.get("status", "")),
            deadline_cell(t.get("deadline"), wide=wide),
            amount_cell(t.get("amount")),
        ]
        if wide:
            row.append(_truncate(t.get("issuer", ""), 30))
        table.add_row(*row)

    c.print(table)
    c.print(summary_bar(
        "tenders",
        total=data.get("total", data.get("count", len(tenders))),
        limit=data.get("limit"),
        offset=data.get("offset", 0),
        query_ms=data.get("_query_ms"),
    ))


def render_bids(data: dict, con=None) -> None:
    """Render bids list. v9 schema with entity_slug, workflow_phase, levers.

    Expected shape:
        {"bids": [...], "total": int, "limit": int, "offset": int}
    Each bid: {id, reference, title, entity_slug, status, workflow_phase,
               deadline, amount, levers, assigned_to}
    """
    c = con or console
    if isinstance(data, list):
        bids = data
        _total, _limit, _offset, _query_ms = len(bids), None, 0, None
    else:
        bids = data.get("bids", data.get("items", []))
        _total = data.get("total", len(bids))
        _limit = data.get("limit")
        _offset = data.get("offset", 0)
        _query_ms = data.get("_query_ms")
    wide = _term_wide()

    table = Table(
        show_header=True, header_style="header", show_lines=False,
        pad_edge=False, padding=(0, 1), expand=True,
        row_styles=["", "on #111111"],
    )

    table.add_column("REF", style="reference", no_wrap=True)
    table.add_column("TITLE", style="title", ratio=1, no_wrap=True, overflow="ellipsis")
    table.add_column("ENT", no_wrap=True, justify="center")
    table.add_column("STATUS", no_wrap=True, justify="center")
    if wide:
        table.add_column("PHASE", no_wrap=True, justify="center")
    table.add_column("DUE", no_wrap=True)
    table.add_column("AMOUNT", no_wrap=True, justify="right")
    if wide:
        table.add_column("LEVERS", no_wrap=True)
        table.add_column("OWNER", style="dim", no_wrap=True)

    for b in bids:
        ref = b.get("reference", "")
        row = [
            str(ref),
            _truncate(b.get("title", ""), 40 if wide else 22),
            entity_badge(b.get("entity_slug", "")),
            status_badge(b.get("status", "")),
        ]
        if wide:
            row.append(phase_badge(b.get("workflow_phase", "")))
        row += [
            deadline_cell(b.get("deadline"), wide=wide),
            amount_cell(b.get("amount")),
        ]
        if wide:
            row.append(levers_cell(b.get("levers")))
            row.append(b.get("assigned_to") or "—")
        table.add_row(*row)

    c.print(table)
    c.print(summary_bar(
        "bids",
        total=_total,
        limit=_limit,
        offset=_offset,
        query_ms=_query_ms,
    ))


def render_entities(data: dict, con=None) -> None:
    """Render entities list. v9 schema with slug, label, margins, team_leads.

    Expected shape:
        {"entities": [...]}
    Each entity: {slug, name, label, notification_channel, team_leads,
                  default_markup, default_overhead, default_contingency, default_risk_premium}
    """
    c = con or console
    entities = data.get("entities", [])
    wide = _term_wide()

    table = Table(
        show_header=True, header_style="header", show_lines=False,
        pad_edge=False, padding=(0, 1), expand=True,
        row_styles=["", "on #111111"],
    )

    table.add_column("SLUG", style="entity.slug", no_wrap=True)
    table.add_column("NAME", style="label", ratio=2, no_wrap=True, overflow="ellipsis")
    table.add_column("LABEL", style="entity.label", ratio=1, no_wrap=True, overflow="ellipsis")
    table.add_column("MARGINS", no_wrap=True)
    table.add_column("NOTIF", no_wrap=True)
    if wide:
        table.add_column("LEADS", style="dim", no_wrap=True, overflow="ellipsis")

    for e in entities:
        margins = {
            "markup": e.get("default_markup", 0),
            "overhead": e.get("default_overhead", 0),
            "contingency": e.get("default_contingency", 0),
            "risk_premium": e.get("default_risk_premium", 0),
        }
        row = [
            str(e.get("slug", "")),
            str(e.get("name", "")),
            str(e.get("label", "")),
            levers_cell(margins),
            notification_cell(e.get("notification_channel")),
        ]
        if wide:
            leads = e.get("team_leads", [])
            row.append(", ".join(leads) if leads else "—")
        table.add_row(*row)

    c.print(table)
    c.print(summary_bar("entities", total=len(entities)))


def render_status_dashboard(data: dict, con=None) -> None:
    """Dashboard view — KPI strip + status bars + platform counts.

    Expected data shape:
        {"by_status": {"open": int, ...}, "by_platform": {"ePerolehan": int, ...},
         "by_entity": {...}, "deadlines_today": int, "total_value": float,
         "total_bids": int, "pipeline_value": float, "win_rate": float}

    Also handles sec-tenders-api stats shape:
        {"total": int, "documents": int, "by_scraper": [...], "by_status": [...]}
    """
    c = con or console

    # Normalize — handle both dict and list-of-dicts shapes from sec API
    by_status = data.get("by_status", {})
    by_platform = data.get("by_platform", {})

    # sec-tenders-api returns lists: [{"status": "x", "count": N}, ...]
    if isinstance(by_status, list):
        by_status = {s.get("status", ""): s.get("count", 0) for s in by_status}
    by_scraper = data.get("by_scraper", [])
    if isinstance(by_scraper, list) and not by_platform:
        by_platform = {s.get("scraper", ""): s.get("count", 0) for s in by_scraper}

    # KPI strip
    total = data.get("total_bids", data.get("total", 0))
    dl_today = data.get("deadlines_today", 0)
    total_val = data.get("total_value", 0)
    pipeline_val = data.get("pipeline_value", 0)
    win_rate = data.get("win_rate", 0)
    docs = data.get("documents", 0)

    # Row 1: header + operational counts
    kpi = Text()
    kpi.append(" DASHBOARD ", style="bold bright_white on blue")
    kpi.append(f"  {total} bids", style="summary.count")
    if docs:
        kpi.append(f"  {docs} docs", style="summary.count")
    if dl_today:
        kpi.append(f"  {dl_today} due today", style="alert.high")
    c.print(kpi)

    # Row 2: financial summary
    kpi2 = Text()
    if total_val:
        kpi2.append(f"  RM {total_val:,.0f} total", style="amount")
    if pipeline_val:
        kpi2.append(f"  RM {pipeline_val:,.0f} pipeline", style="summary.label")
    if win_rate:
        pct = int(win_rate * 100)
        style = "bold bright_green" if pct >= 50 else "alert.mid" if pct >= 30 else "alert.high"
        kpi2.append(f"  {pct}% win rate", style=style)
    if kpi2.plain.strip():
        c.print(kpi2)
    c.print()

    # Status breakdown with horizontal bars
    if by_status:
        max_count = max(by_status.values()) if by_status else 1
        bar_width = 15 if not _term_wide() else 25

        for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
            bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
            line = Text()
            line.append(f" {status.upper():<12s}", style=_status_style(status))
            line.append(f" {count:>3d} ", style="summary.count")
            line.append("\u2588" * bar_len, style=_status_style(status))
            c.print(line)

        c.print()

    # Platform counts inline
    if by_platform:
        plat = Text()
        for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
            plat.append(f" {platform} ", style="bold bright_white on bright_black")
            plat.append(f" {count} ", style="summary.count")
            plat.append("  ")
        c.print(plat)

    # Entity counts (v9)
    by_entity = data.get("by_entity", {})
    if by_entity:
        c.print()
        ent = Text()
        for slug, count in sorted(by_entity.items(), key=lambda x: -x[1]):
            ent.append(f" {slug} ", style="entity.slug")
            ent.append(f" {count} ", style="summary.count")
            ent.append("  ")
        c.print(ent)


def _status_style(status: str) -> str:
    return STATUS_STYLE_MAP.get(status.lower(), "dim")


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "\u2026"
