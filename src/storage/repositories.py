"""SQLite repository helpers."""

from __future__ import annotations

import sqlite3

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
