"""SQLite repository helpers."""

from __future__ import annotations

import sqlite3
from typing import Any

import pandas as pd


MARKET_CANDLE_COLUMNS = [
    "exchange",
    "symbol",
    "timeframe",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "fetched_at",
]
ALERT_COLUMNS = [
    "alert_type",
    "severity",
    "severity_score",
    "exchange",
    "symbol",
    "start_time",
    "end_time",
    "evidence_summary",
    "recommended_follow_up",
    "dedup_key",
    "created_at",
]


def insert_market_candles(conn: sqlite3.Connection, candles: pd.DataFrame) -> int:
    """Insert market candles, skipping duplicate exchange/symbol/timeframe/timestamp rows."""
    if candles.empty:
        return 0

    missing_columns = set(MARKET_CANDLE_COLUMNS).difference(candles.columns)
    if missing_columns:
        raise ValueError(f"Market candles missing columns: {sorted(missing_columns)}")

    before_changes = conn.total_changes
    rows = [
        tuple(row[column] for column in MARKET_CANDLE_COLUMNS)
        for row in candles[MARKET_CANDLE_COLUMNS].to_dict("records")
    ]
    conn.executemany(
        """
        INSERT INTO market_candles (
            exchange,
            symbol,
            timeframe,
            timestamp,
            open,
            high,
            low,
            close,
            volume,
            fetched_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(exchange, symbol, timeframe, timestamp) DO NOTHING
        """,
        rows,
    )
    conn.commit()
    return conn.total_changes - before_changes


def insert_alerts(conn: sqlite3.Connection, alerts: pd.DataFrame) -> int:
    """Insert alerts and evidence, preserving existing deduplicated alerts."""
    if alerts.empty:
        return 0

    missing_columns = set(ALERT_COLUMNS).difference(alerts.columns)
    if missing_columns:
        raise ValueError(f"Alerts missing columns: {sorted(missing_columns)}")

    inserted_count = 0
    for alert in alerts.to_dict("records"):
        values = tuple(_none_if_missing(alert[column]) for column in ALERT_COLUMNS)
        cursor = conn.execute(
            """
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
            """,
            values,
        )
        if cursor.rowcount == 1:
            inserted_count += 1
            alert_id = int(cursor.lastrowid)
            _insert_alert_evidence(conn, alert_id, alert.get("evidence", []))

    conn.commit()
    return inserted_count


def _insert_alert_evidence(
    conn: sqlite3.Connection, alert_id: int, evidence_items: Any
) -> None:
    if not evidence_items:
        return
    rows = [
        (
            alert_id,
            str(item["metric_name"]),
            _none_if_missing(item.get("metric_value")),
            _none_if_missing(item.get("threshold_value")),
            item.get("comparison_operator"),
            str(item["explanation"]),
        )
        for item in evidence_items
    ]
    conn.executemany(
        """
        INSERT INTO alert_evidence (
            alert_id,
            metric_name,
            metric_value,
            threshold_value,
            comparison_operator,
            explanation
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _none_if_missing(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value
