"""Fetch, normalize, and fallback-load public OHLCV market candles."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FALLBACK_PATH = PROJECT_ROOT / "data" / "sample_market_candles.csv"
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
DEFAULT_SYMBOL_BASE_PRICES = {
    "BTC/USD": 68_000.0,
    "ETH/USD": 3_200.0,
    "SOL/USD": 160.0,
}
SAMPLE_END_TIME = datetime(2026, 5, 23, 0, 0, tzinfo=UTC)
SAMPLE_FETCHED_AT = SAMPLE_END_TIME.isoformat()


def fetch_ohlcv(
    exchange_id: str, symbols: list[str], timeframe: str, limit: int
) -> pd.DataFrame:
    """Fetch OHLCV candles from a CCXT exchange and normalize them."""
    if not symbols:
        raise ValueError("At least one symbol is required.")
    if limit <= 0:
        raise ValueError("limit must be positive.")

    exchange = _build_exchange(exchange_id)
    _load_markets(exchange)

    frames: list[pd.DataFrame] = []
    batch_fetched_at = _utc_now_iso()
    for symbol in symbols:
        _ensure_symbol_supported(exchange, symbol)
        rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not rows:
            raise ValueError(f"No OHLCV rows returned for {exchange_id} {symbol}.")
        frame = normalize_ohlcv(rows, exchange_id, symbol, timeframe)
        frame["fetched_at"] = batch_fetched_at
        frames.append(frame)

    candles = _drop_invalid_close_prices(pd.concat(frames, ignore_index=True))
    _attach_attrs(
        candles,
        data_source="live",
        api_status="ok",
        exchange=exchange_id,
        timeframe=timeframe,
        fallback_reason="",
    )
    candles.attrs["last_fetched_at"] = batch_fetched_at
    return candles


def _drop_invalid_close_prices(candles: pd.DataFrame) -> pd.DataFrame:
    """Drop implausible close prices from one fetched OHLCV batch."""
    if candles.empty:
        return candles

    frame = candles.copy()
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    group_columns = ["exchange", "symbol", "timeframe"]
    frame["batch_median_close"] = frame.groupby(group_columns)["close"].transform("median")
    invalid_close = frame["close"].isna()
    invalid_close |= frame["close"] < (frame["batch_median_close"] * 0.10)
    invalid_close |= frame["symbol"].astype(str).str.contains("BTC", case=False, na=False) & (
        frame["close"] < 1000
    )

    for row in frame[invalid_close].to_dict("records"):
        LOGGER.warning(
            "Dropping invalid OHLCV close price: exchange=%s symbol=%s timeframe=%s "
            "timestamp=%s close=%s batch_median_close=%s",
            row.get("exchange"),
            row.get("symbol"),
            row.get("timeframe"),
            row.get("timestamp"),
            row.get("close"),
            row.get("batch_median_close"),
        )

    return frame.loc[~invalid_close, MARKET_CANDLE_COLUMNS].reset_index(drop=True)


def normalize_ohlcv(
    raw_rows: list[list[Any]], exchange: str, symbol: str, timeframe: str
) -> pd.DataFrame:
    """Normalize CCXT OHLCV rows into the market_candles schema columns."""
    if not raw_rows:
        raise ValueError(f"No OHLCV rows to normalize for {exchange} {symbol}.")

    fetched_at = _utc_now_iso()
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows):
        if not isinstance(row, list | tuple) or len(row) < 6:
            raise ValueError(f"Malformed OHLCV row at index {index}: expected 6 values.")
        try:
            timestamp_ms = float(row[0])
            open_price = float(row[1])
            high = float(row[2])
            low = float(row[3])
            close = float(row[4])
            volume = float(row[5])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Malformed OHLCV row at index {index}: non-numeric value.") from exc

        numeric_values = [timestamp_ms, open_price, high, low, close, volume]
        if not np.isfinite(numeric_values).all():
            raise ValueError(f"Malformed OHLCV row at index {index}: non-finite value.")

        normalized.append(
            {
                "exchange": exchange,
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": _timestamp_ms_to_iso(timestamp_ms),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "fetched_at": fetched_at,
            }
        )

    return pd.DataFrame(normalized, columns=MARKET_CANDLE_COLUMNS)


def load_market_data(
    exchange_id: str,
    symbols: list[str],
    timeframe: str,
    limit: int,
    fallback_path: str,
) -> pd.DataFrame:
    """Fetch live candles, falling back to deterministic sample data on API failure."""
    try:
        candles = fetch_ohlcv(exchange_id, symbols, timeframe, limit)
    except Exception as exc:  # noqa: BLE001 - fallback should cover CCXT/runtime failures.
        reason = f"{type(exc).__name__}: {exc}"
        LOGGER.warning("Using sample market candles after ingestion failure: %s", reason)
        return _load_fallback_market_data(
            fallback_path=fallback_path,
            exchange_id=exchange_id,
            timeframe=timeframe,
            reason=reason,
        )

    if candles.empty:
        reason = "empty live response"
        LOGGER.warning("Using sample market candles after ingestion failure: %s", reason)
        return _load_fallback_market_data(
            fallback_path=fallback_path,
            exchange_id=exchange_id,
            timeframe=timeframe,
            reason=reason,
        )
    return candles


def generate_sample_market_candles(
    symbols: list[str] | None = None,
    exchange: str = "coinbase",
    timeframe: str = "5m",
    periods: int = 100,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate deterministic sample market candles for offline fallback."""
    if periods <= 0:
        raise ValueError("periods must be positive.")

    selected_symbols = symbols or list(DEFAULT_SYMBOL_BASE_PRICES)
    rng = np.random.default_rng(seed)
    start_time = SAMPLE_END_TIME - timedelta(minutes=5 * (periods - 1))
    rows: list[dict[str, Any]] = []

    for symbol_index, symbol in enumerate(selected_symbols):
        base_price = DEFAULT_SYMBOL_BASE_PRICES.get(symbol, 100.0)
        close = base_price * (1.0 + symbol_index * 0.01)
        for period_index in range(periods):
            timestamp = start_time + timedelta(minutes=5 * period_index)
            drift = 1.0 + (period_index * 0.0001)
            open_price = close
            close = open_price * drift * (1.0 + float(rng.normal(0, 0.0015)))
            high = max(open_price, close) * (1.0 + abs(float(rng.normal(0, 0.0008))))
            low = min(open_price, close) * (1.0 - abs(float(rng.normal(0, 0.0008))))
            volume = abs(float(rng.normal(1000, 180))) * (symbol_index + 1)
            rows.append(
                {
                    "exchange": exchange,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": timestamp.isoformat(),
                    "open": round(open_price, 6),
                    "high": round(high, 6),
                    "low": round(low, 6),
                    "close": round(close, 6),
                    "volume": round(volume, 6),
                    "fetched_at": SAMPLE_FETCHED_AT,
                }
            )

    return pd.DataFrame(rows, columns=MARKET_CANDLE_COLUMNS)


def export_sample_market_candles(
    output_path: str | Path = DEFAULT_FALLBACK_PATH, seed: int = 42
) -> Path:
    """Export deterministic fallback market candles to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    generate_sample_market_candles(seed=seed).to_csv(path, index=False)
    return path


def _build_exchange(exchange_id: str) -> Any:
    try:
        import ccxt  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("ccxt is not installed.") from exc

    exchange_class = getattr(ccxt, exchange_id, None)
    if exchange_class is None:
        raise ValueError(f"Unsupported CCXT exchange: {exchange_id}.")
    return exchange_class({"enableRateLimit": True, "timeout": 10_000})


def _load_markets(exchange: Any) -> None:
    load_markets = getattr(exchange, "load_markets", None)
    if callable(load_markets):
        load_markets()


def _ensure_symbol_supported(exchange: Any, symbol: str) -> None:
    symbols = getattr(exchange, "symbols", None)
    if symbols is not None and symbol not in symbols:
        raise ValueError(f"Unsupported symbol for exchange: {symbol}.")


def _load_fallback_market_data(
    fallback_path: str, exchange_id: str, timeframe: str, reason: str
) -> pd.DataFrame:
    path = Path(fallback_path)
    if not path.exists() or path.stat().st_size == 0:
        export_sample_market_candles(path)
    try:
        candles = pd.read_csv(path)
        missing_columns = set(MARKET_CANDLE_COLUMNS).difference(candles.columns)
        if missing_columns:
            raise ValueError(f"Fallback market data missing columns: {sorted(missing_columns)}")
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError, ValueError) as exc:
        LOGGER.warning("Regenerating sample market candles after fallback load failure: %s", exc)
        export_sample_market_candles(path)
        candles = pd.read_csv(path)
    candles = candles[MARKET_CANDLE_COLUMNS]
    _attach_attrs(
        candles,
        data_source="sample",
        api_status="unavailable",
        exchange=exchange_id,
        timeframe=timeframe,
        fallback_reason=reason,
    )
    return candles


def _attach_attrs(
    candles: pd.DataFrame,
    data_source: str,
    api_status: str,
    exchange: str,
    timeframe: str,
    fallback_reason: str,
) -> None:
    candles.attrs["data_source"] = data_source
    candles.attrs["api_status"] = api_status
    candles.attrs["exchange"] = exchange
    candles.attrs["timeframe"] = timeframe
    candles.attrs["fallback_reason"] = fallback_reason
    candles.attrs["last_fetched_at"] = _latest_value(candles, "fetched_at")
    candles.attrs["latest_candle_timestamp"] = _latest_value(candles, "timestamp")


def _latest_value(candles: pd.DataFrame, column: str) -> str:
    if candles.empty or column not in candles:
        return ""
    return str(pd.to_datetime(candles[column], utc=True).max().isoformat())


def _timestamp_ms_to_iso(timestamp_ms: float) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).replace(microsecond=0).isoformat()


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
