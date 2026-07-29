"""Bid management and status tracking command."""

from ..db import query_bids
from ..formatters import format_bids


def handle_bids(
    entity: str | None = None,
    status: str | None = None,
    phase: str | None = None,
    limit: int = 50,
    offset: int = 0,
    as_json: bool = False,
) -> None:
    bids = query_bids(entity=entity, status=status, phase=phase, limit=limit, offset=offset)
    data = {"bids": bids, "total": len(bids), "limit": limit, "offset": offset}
    format_bids(data, as_json=as_json)
