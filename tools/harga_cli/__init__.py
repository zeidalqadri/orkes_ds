"""harga_cli — Bloomberg-style terminal rendering for Malaysian procurement."""

__version__ = "0.2.0"

from .theme import console, HARGA_THEME
from .tables import render_tenders, render_bids, render_entities, render_status_dashboard
from .panels import (
    header_bar, summary_bar, status_badge, platform_badge, phase_badge,
    entity_badge, deadline_cell, amount_cell, levers_cell, notification_cell,
)
