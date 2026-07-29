"""Test fixtures and configuration for harga-cli tests."""

import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_harga_db():
    """Create a temporary harga_v8.db for testing.

    Yields:
        sqlite3.Connection: Test database connection
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Create schema (builders: match actual harga_v8.db schema)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            telegram_chat_id INTEGER
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY,
            tender_id TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            deadline TEXT,
            amount REAL,
            created_at TEXT,
            FOREIGN KEY(entity_id) REFERENCES entities(id)
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY,
            action TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """
    )

    conn.commit()

    yield conn

    conn.close()
    db_path.unlink()


@pytest.fixture
def temp_tenders_db():
    """Create a temporary tenders.db for testing.

    Yields:
        sqlite3.Connection: Test database connection
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Create schema (builders: match actual tenders.db schema)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tenders (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            entity TEXT NOT NULL,
            status TEXT NOT NULL,
            deadline TEXT,
            amount REAL
        )
    """
    )

    conn.commit()

    yield conn

    conn.close()
    db_path.unlink()


@pytest.fixture
def sample_entities(temp_harga_db):
    """Insert sample entities into test database.

    Args:
        temp_harga_db: Test database connection

    Returns:
        list: List of inserted entity IDs
    """
    entities = [
        ("BuzzBuzz", 123456),
        ("TechCorp", 654321),
        ("ServicesPro", None),
    ]

    cursor = temp_harga_db.cursor()
    for name, chat_id in entities:
        cursor.execute("INSERT INTO entities (name, telegram_chat_id) VALUES (?, ?)", (name, chat_id))
    temp_harga_db.commit()

    return [row[0] for row in cursor.execute("SELECT id FROM entities")]


@pytest.fixture
def sample_tenders(temp_tenders_db):
    """Insert sample tenders into test database.

    Args:
        temp_tenders_db: Test database connection

    Returns:
        list: List of inserted tender IDs
    """
    tenders = [
        ("EPE-2026-00123", "Office Supplies", "ePerolehan", "open", "2026-08-15T17:00:00Z", 50000),
        ("FSH-2026-00456", "IT Services", "ForSAH", "open", "2026-08-20T17:00:00Z", 150000),
        ("ETI-2026-00789", "Construction", "eTimad", "closed", "2026-07-20T17:00:00Z", 500000),
    ]

    cursor = temp_tenders_db.cursor()
    for tender_id, title, entity, status, deadline, amount in tenders:
        cursor.execute(
            "INSERT INTO tenders (id, title, entity, status, deadline, amount) VALUES (?, ?, ?, ?, ?, ?)",
            (tender_id, title, entity, status, deadline, amount),
        )
    temp_tenders_db.commit()

    return [row[0] for row in cursor.execute("SELECT id FROM tenders")]
