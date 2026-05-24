"""SQLite connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_sqlite(db_path: str | Path = ":memory:") -> sqlite3.Connection:
    """Open a SQLite connection with foreign key enforcement enabled."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn
