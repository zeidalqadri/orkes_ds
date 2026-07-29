"""Output formatting — Rich tables (default) or JSON fallback."""

import json
from typing import Any

from .tables import render_tenders, render_bids, render_entities, render_status_dashboard
from .theme import console


def format_tenders(data: dict[str, Any], as_json: bool = False) -> None:
    if as_json:
        console.print_json(json.dumps(data))
    else:
        render_tenders(data)


def format_bids(data: dict[str, Any], as_json: bool = False) -> None:
    if as_json:
        console.print_json(json.dumps(data))
    else:
        render_bids(data)


def format_entities(data: dict[str, Any], as_json: bool = False) -> None:
    if as_json:
        console.print_json(json.dumps(data))
    else:
        render_entities(data)


def format_status(data: dict[str, Any], as_json: bool = False) -> None:
    if as_json:
        console.print_json(json.dumps(data))
    else:
        render_status_dashboard(data)
