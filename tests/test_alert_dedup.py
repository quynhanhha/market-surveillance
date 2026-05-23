"""Alert deduplication schema tests."""

from __future__ import annotations

import sqlite3

import pytest

from src.storage.db import connect_sqlite
from src.storage.schema import create_schema


def test_alert_dedup_key_unique_constraint_supports_conflict_skip() -> None:
    """Alert inserts can use ON CONFLICT(dedup_key) DO NOTHING."""
    conn = connect_sqlite()
    create_schema(conn)

    insert_sql = """
        INSERT INTO alerts (
            alert_type,
            severity,
            severity_score,
            exchange,
            symbol,
            start_time,
            end_time,
            evidence_summary,
            recommended_follow_up,
            dedup_key,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(dedup_key) DO NOTHING
    """
    values = (
        "Volume Spike",
        "Low",
        15,
        "binance",
        "BTC/USDT",
        "2026-05-23T10:00:00+00:00",
        "2026-05-23T10:05:00+00:00",
        "Synthetic test alert",
        None,
        "same-dedup-key",
        "2026-05-23T10:06:00+00:00",
    )
    conn.execute(insert_sql, values)
    conn.execute(insert_sql, values)

    count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    assert count == 1


def test_alert_evidence_rejects_unknown_alert() -> None:
    """Foreign key constraints are active after schema initialization."""
    conn = connect_sqlite()
    create_schema(conn)

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO alert_evidence (
                alert_id,
                metric_name,
                metric_value,
                threshold_value,
                comparison_operator,
                explanation
            )
            VALUES (999, 'volume_z_score', 4.2, 3.0, '>', 'Missing alert')
            """
        )
