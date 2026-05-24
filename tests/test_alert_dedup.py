"""Alert deduplication schema tests."""

from __future__ import annotations

import sqlite3
import subprocess
import sys

import pandas as pd
import pytest

from src.detection.severity import make_dedup_key
from src.storage.db import connect_sqlite
from src.storage.repositories import insert_alerts
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


def test_insert_alerts_skips_duplicate_dedup_key_and_preserves_status() -> None:
    """Duplicate alert insertion preserves analyst status and evidence."""
    conn = connect_sqlite()
    create_schema(conn)
    alerts = alert_frame("BTC/USDT")

    assert insert_alerts(conn, alerts) == 1
    conn.execute("UPDATE alerts SET status = 'Under Review'")
    assert insert_alerts(conn, alerts) == 0

    row = conn.execute("SELECT status, created_at FROM alerts").fetchone()
    alert_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    evidence_count = conn.execute("SELECT COUNT(*) FROM alert_evidence").fetchone()[0]
    assert alert_count == 1
    assert evidence_count == 1
    assert row["status"] == "Under Review"
    assert row["created_at"] == "2026-05-23T10:00:00+00:00"


def test_insert_alerts_allows_different_symbol_same_type() -> None:
    """Different alert subjects produce different dedup keys and rows."""
    conn = connect_sqlite()
    create_schema(conn)

    assert insert_alerts(conn, alert_frame("BTC/USDT")) == 1
    assert insert_alerts(conn, alert_frame("ETH/USDT")) == 1

    count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    assert count == 2


def test_dedup_key_is_deterministic_across_processes() -> None:
    """The same dedup inputs produce the same key in separate Python processes."""
    code = (
        "from src.detection.severity import make_dedup_key; "
        "print(make_dedup_key('Volume Spike', 'BTC/USDT', "
        "'2026-05-23T10:00:00+00:00', '2026-05-23T10:00:00+00:00'))"
    )

    first = subprocess.check_output([sys.executable, "-c", code], text=True).strip()
    second = subprocess.check_output([sys.executable, "-c", code], text=True).strip()

    assert first == second == make_dedup_key(
        "Volume Spike",
        "BTC/USDT",
        "2026-05-23T10:00:00+00:00",
        "2026-05-23T10:00:00+00:00",
    )


def alert_frame(symbol: str):
    """Build one alert row with one evidence item."""
    start_time = "2026-05-23T10:00:00+00:00"
    return pd.DataFrame(
        [
            {
                "alert_type": "Volume Spike",
                "severity": "Low",
                "severity_score": 15,
                "exchange": "coinbase",
                "symbol": symbol,
                "start_time": start_time,
                "end_time": start_time,
                "account_id": None,
                "evidence_summary": "Synthetic test alert",
                "recommended_follow_up": None,
                "dedup_key": make_dedup_key("Volume Spike", symbol, start_time, start_time),
                "created_at": start_time,
                "evidence": [
                    {
                        "metric_name": "volume_z_score",
                        "metric_value": 3.5,
                        "threshold_value": 3.0,
                        "comparison_operator": ">",
                        "explanation": "Test evidence",
                    }
                ],
            }
        ]
    )
