"""SQLite repository helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
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
    "account_id",
    "start_time",
    "end_time",
    "evidence_summary",
    "recommended_follow_up",
    "dedup_key",
    "created_at",
]
SYNTHETIC_TABLE_FILES = {
    "accounts": "sample_accounts.csv",
    "account_links": "sample_account_links.csv",
    "synthetic_orders": "sample_synthetic_orders.csv",
    "synthetic_trades": "sample_synthetic_trades.csv",
}
VALID_ALERT_STATUSES = {"New", "Under Review", "Escalated", "Closed"}


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
                account_id,
                start_time,
                end_time,
                evidence_summary,
                recommended_follow_up,
                dedup_key,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def load_synthetic_tables(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Load committed deterministic synthetic CSV tables."""
    tables: dict[str, pd.DataFrame] = {}
    for table_name, file_name in SYNTHETIC_TABLE_FILES.items():
        path = data_dir / file_name
        tables[table_name] = pd.read_csv(path) if path.exists() else pd.DataFrame()
    return tables


def insert_synthetic_tables(
    conn: sqlite3.Connection, tables: dict[str, pd.DataFrame]
) -> dict[str, int]:
    """Insert synthetic tables with primary-key deduplication."""
    inserted: dict[str, int] = {}
    for table_name in ("accounts", "account_links", "synthetic_orders", "synthetic_trades"):
        frame = tables.get(table_name, pd.DataFrame())
        if frame.empty:
            inserted[table_name] = 0
            continue
        before_changes = conn.total_changes
        columns = list(frame.columns)
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(columns)
        conn.executemany(
            f"INSERT OR IGNORE INTO {table_name} ({column_sql}) VALUES ({placeholders})",
            [tuple(row[column] for column in columns) for row in frame.to_dict("records")],
        )
        inserted[table_name] = conn.total_changes - before_changes
    conn.commit()
    return inserted


def fetch_alerts(
    conn: sqlite3.Connection, filters: dict[str, Any] | None = None
) -> pd.DataFrame:
    """Fetch alerts for UI and reporting, applying optional SQL-side filters."""
    filters = filters or {}
    where: list[str] = []
    params: list[Any] = []
    for column in ("exchange", "symbol", "severity", "status", "alert_type"):
        values = _as_filter_values(filters.get(column))
        if values:
            placeholders = ", ".join("?" for _ in values)
            where.append(f"{column} IN ({placeholders})")
            params.extend(values)
    if start_time := filters.get("start_time"):
        where.append("end_time >= ?")
        params.append(str(start_time))
    if end_time := filters.get("end_time"):
        where.append("start_time <= ?")
        params.append(str(end_time))

    query = "SELECT * FROM alerts"
    if where:
        query = f"{query} WHERE {' AND '.join(where)}"
    query = f"{query} ORDER BY severity_score DESC, end_time DESC, alert_id DESC"
    return pd.read_sql_query(query, conn, params=params)


def fetch_alert_evidence(conn: sqlite3.Connection, alert_id: int) -> pd.DataFrame:
    """Fetch evidence rows for one alert."""
    return pd.read_sql_query(
        """
        SELECT evidence_id, alert_id, metric_name, metric_value, threshold_value,
               comparison_operator, explanation
        FROM alert_evidence
        WHERE alert_id = ?
        ORDER BY evidence_id
        """,
        conn,
        params=[alert_id],
    )


def update_alert_status(conn: sqlite3.Connection, alert_id: int, status: str) -> None:
    """Persist an analyst status update for an alert."""
    if status not in VALID_ALERT_STATUSES:
        raise ValueError(f"Invalid alert status: {status}")
    conn.execute("UPDATE alerts SET status = ? WHERE alert_id = ?", (status, alert_id))
    conn.commit()


def fetch_market_candles(
    conn: sqlite3.Connection, filters: dict[str, Any] | None = None
) -> pd.DataFrame:
    """Fetch stored market candles for charting."""
    filters = filters or {}
    where: list[str] = []
    params: list[Any] = []
    for column in ("exchange", "symbol", "timeframe"):
        values = _as_filter_values(filters.get(column))
        if values:
            placeholders = ", ".join("?" for _ in values)
            where.append(f"{column} IN ({placeholders})")
            params.extend(values)
    if start_time := filters.get("start_time"):
        where.append("timestamp >= ?")
        params.append(str(start_time))
    if end_time := filters.get("end_time"):
        where.append("timestamp <= ?")
        params.append(str(end_time))
    query = "SELECT * FROM market_candles"
    if where:
        query = f"{query} WHERE {' AND '.join(where)}"
    query = f"{query} ORDER BY timestamp"
    return pd.read_sql_query(query, conn, params=params)


def fetch_table(conn: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    """Fetch a known storage table."""
    allowed = {"accounts", "account_links", "synthetic_orders", "synthetic_trades"}
    if table_name not in allowed:
        raise ValueError(f"Unsupported table: {table_name}")
    return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)


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


def _as_filter_values(value: Any) -> list[Any]:
    if value is None or value == "All":
        return []
    if isinstance(value, str):
        return [value]
    return [item for item in value if item != "All"]
