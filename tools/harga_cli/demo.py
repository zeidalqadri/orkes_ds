#!/usr/bin/env python3
"""Demo runner — shows all views with sample data.

Usage:
    python -m tools.harga_cli.demo           # all views
    python -m tools.harga_cli.demo tenders   # single view
"""

import sys
from . import __version__
from .theme import console
from .panels import header_bar
from .tables import render_tenders, render_bids, render_entities, render_status_dashboard
from .sample_data import SAMPLE_DATA


def demo_all():
    console.print(header_bar("HARGA", __version__))
    console.print()

    console.rule("[header]TENDERS[/header]", style="dim")
    render_tenders(SAMPLE_DATA["tenders"])
    console.print()

    console.rule("[header]BIDS[/header]", style="dim")
    render_bids(SAMPLE_DATA["bids"])
    console.print()

    console.rule("[header]ENTITIES[/header]", style="dim")
    render_entities(SAMPLE_DATA["entities"])
    console.print()

    console.rule("[header]STATUS DASHBOARD[/header]", style="dim")
    render_status_dashboard(SAMPLE_DATA["status"])
    console.print()


def demo_one(view: str):
    console.print(header_bar("HARGA", __version__))
    console.print()

    renderers = {
        "tenders": lambda: render_tenders(SAMPLE_DATA["tenders"]),
        "bids": lambda: render_bids(SAMPLE_DATA["bids"]),
        "entities": lambda: render_entities(SAMPLE_DATA["entities"]),
        "status": lambda: render_status_dashboard(SAMPLE_DATA["status"]),
    }

    if view in renderers:
        renderers[view]()
    else:
        console.print(f"[alert.high]Unknown view: {view}[/alert.high]")
        console.print(f"Available: {', '.join(renderers)}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        demo_one(sys.argv[1])
    else:
        demo_all()
