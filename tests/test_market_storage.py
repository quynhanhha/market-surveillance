"""Market candle repository tests."""

from __future__ import annotations

from src.ingestion.fetch_market_data import generate_sample_market_candles
from src.storage.db import connect_sqlite
from src.storage.repositories import insert_market_candles
from src.storage.schema import create_schema


def test_insert_market_candles_skips_duplicate_unique_keys() -> None:
    """Duplicate market candles are ignored without updating existing rows."""
    conn = connect_sqlite()
    create_schema(conn)
    candles = generate_sample_market_candles(symbols=["BTC/USD"], periods=3)

    first_insert_count = insert_market_candles(conn, candles)
    second_insert_count = insert_market_candles(conn, candles)

    row_count = conn.execute("SELECT COUNT(*) FROM market_candles").fetchone()[0]
    assert first_insert_count == 3
    assert second_insert_count == 0
    assert row_count == 3


def test_fallback_candles_insert_without_duplicates() -> None:
    """Generated fallback candles load into the schema with conflict protection."""
    conn = connect_sqlite()
    create_schema(conn)
    candles = generate_sample_market_candles(periods=2)

    assert insert_market_candles(conn, candles) == 6
    assert insert_market_candles(conn, candles) == 0
