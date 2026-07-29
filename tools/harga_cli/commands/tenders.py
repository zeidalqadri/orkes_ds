"""Tender listing and filtering command."""

from ..db import query_tenders
from ..formatters import format_tenders


def handle_tenders(
    portal: str | None = None,
    status: str | None = None,
    buyer: str | None = None,
    limit: int = 50,
    offset: int = 0,
    as_json: bool = False,
) -> None:
    tenders = query_tenders(portal=portal, status=status, buyer=buyer, limit=limit, offset=offset)
    data = {"tenders": tenders, "total": len(tenders), "limit": limit, "offset": offset}
    format_tenders(data, as_json=as_json)
