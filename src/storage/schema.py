"""SQLite schema initialization."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "sql" / "create_tables.sql"


def load_schema_sql(schema_path: Path = SCHEMA_PATH) -> str:
    """Return the project SQLite schema SQL."""
    return schema_path.read_text(encoding="utf-8")


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all database tables and constraints for the application."""
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(load_schema_sql())
    conn.commit()
