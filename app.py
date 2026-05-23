"""Streamlit entrypoint for the surveillance dashboard."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.ingestion.fetch_market_data import load_market_data
from src.storage.db import connect_sqlite
from src.storage.repositories import insert_market_candles
from src.storage.schema import create_schema


APP_TITLE = "Crypto Market Surveillance Analytics"
PROJECT_ROOT = Path(__file__).resolve().parent
FALLBACK_PATH = PROJECT_ROOT / "data" / "sample_market_candles.csv"
DEFAULT_EXCHANGE = "coinbase"
DEFAULT_SYMBOLS = ["BTC/USD", "ETH/USD", "SOL/USD"]
DEFAULT_TIMEFRAME = "5m"
DEFAULT_LIMIT = 100


def main() -> None:
    """Render the market ingestion dashboard."""
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    conn = connect_sqlite()
    create_schema(conn)
    candles = load_market_data(
        exchange_id=DEFAULT_EXCHANGE,
        symbols=DEFAULT_SYMBOLS,
        timeframe=DEFAULT_TIMEFRAME,
        limit=DEFAULT_LIMIT,
        fallback_path=str(FALLBACK_PATH),
    )
    inserted_count = insert_market_candles(conn, candles)

    st.title(APP_TITLE)
    data_source = candles.attrs.get("data_source", "sample")
    last_fetched_at = candles.attrs.get("last_fetched_at", "")
    latest_candle_timestamp = candles.attrs.get("latest_candle_timestamp", "")
    if candles.attrs.get("data_source") == "live":
        st.info(f"Data source: Live - last fetched {last_fetched_at} UTC")
    else:
        fallback_reason = candles.attrs.get("fallback_reason", "API unavailable")
        st.warning(f"Data source: Sample fallback - {fallback_reason}")

    metrics = st.columns(5)
    metrics[0].metric("Exchange", candles.attrs.get("exchange", DEFAULT_EXCHANGE))
    metrics[1].metric("Timeframe", candles.attrs.get("timeframe", DEFAULT_TIMEFRAME))
    metrics[2].metric("Data source", data_source.title())
    metrics[3].metric("Rows loaded", f"{len(candles):,}")
    metrics[4].metric("Rows inserted", f"{inserted_count:,}")

    st.caption(
        f"Latest candle timestamp: {latest_candle_timestamp} | "
        f"Last fetch timestamp: {last_fetched_at}"
    )


if __name__ == "__main__":
    main()
