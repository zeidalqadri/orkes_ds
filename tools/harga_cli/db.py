"""Database connection and query templates for harga-cli."""

import sqlite3
from pathlib import Path
from typing import Any, Generator

from .errors import DatabaseError


def get_harga_db() -> sqlite3.Connection:
    """Get connection to harga_v9.db (bids, entities, audit log).

    Returns:
        sqlite3.Connection: Database connection with row factory

    Raises:
        DatabaseError: If connection fails
    """
    db_path = Path("data/harga_v9.db")
    if not db_path.exists():
        raise DatabaseError(f"Database not found: {db_path}")

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to connect to harga_v9.db: {e}")


def get_tenders_db() -> sqlite3.Connection:
    """Get connection to tenders.db (tender intake feed).

    Returns:
        sqlite3.Connection: Database connection with row factory

    Raises:
        DatabaseError: If connection fails
    """
    db_path = Path("data/tenders.db")
    if not db_path.exists():
        raise DatabaseError(f"Database not found: {db_path}")

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to connect to tenders.db: {e}")


def query_tenders(
    portal: str | None = None,
    status: str | None = None,
    buyer: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Query tenders from tenders.db with optional filters.

    Args:
        portal: Filter by portal (ePerolehan, ForSAH, eTimad)
        status: Filter by tender status (open, closed)
        buyer: Filter by buyer slug
        limit: Max results (default: 50)
        offset: Pagination offset (default: 0)

    Returns:
        List of tender records as dicts.
        Each dict: {id, title, portal, reference, status, deadline, amount, issuer, buyer}

    Raises:
        DatabaseError: If query fails
    """
    # Builders: implement query against tenders table
    # Use parameterized SQL to prevent injection
    raise NotImplementedError("query_tenders: builder to implement")


def query_bids(
    entity: str | None = None,
    status: str | None = None,
    phase: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Query bids from harga_v9.db with optional filters.

    Args:
        entity: Filter by entity_slug (consurv-technic, dyna-om, etc.)
        status: Filter by bid status (active, overdue, won, lost, draft, submitted, priced, in_progress)
        phase: Filter by workflow_phase (pricing, approval, packaging, submitted, post_submit)
        limit: Max results (default: 50)
        offset: Pagination offset (default: 0)

    Returns:
        List of bid records as dicts.
        Each dict: {id, reference, title, entity_slug, status, workflow_phase,
                    deadline, amount, levers, assigned_to, source_tender_id, created_at}

    Raises:
        DatabaseError: If query fails
    """
    # Builders: implement query against bids table
    # Join with entities on entity_slug
    raise NotImplementedError("query_bids: builder to implement")


def query_entities() -> list[dict[str, Any]]:
    """Query all entities configured in harga_v9.db.

    Returns:
        List of entity records as dicts.
        Each dict: {slug, name, label, notification_channel, team_leads,
                    default_markup, default_overhead, default_contingency, default_risk_premium}

    Raises:
        DatabaseError: If query fails
    """
    # Builders: implement query against entities table
    raise NotImplementedError("query_entities: builder to implement")


def set_entity_notification(entity_slug: str, channel: str) -> None:
    """Set notification channel for an entity.

    Args:
        entity_slug: Entity slug (e.g. consurv-technic)
        channel: Notification channel string (e.g. tg:198234)

    Raises:
        DatabaseError: If update fails
    """
    # Builders: implement update against entities table
    # Parameterized SQL to prevent injection
    raise NotImplementedError("set_entity_notification: builder to implement")
