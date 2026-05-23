"""Market OHLCV ingestion tests."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src.ingestion.fetch_market_data import (
    MARKET_CANDLE_COLUMNS,
    fetch_ohlcv,
    generate_sample_market_candles,
    load_market_data,
    normalize_ohlcv,
)


def test_normalize_ohlcv_returns_market_candle_schema() -> None:
    """Valid CCXT OHLCV rows become schema-compatible UTC candles."""
    candles = normalize_ohlcv(
        raw_rows=[[1_777_000_000_000, 100, 110, 95, 105, 12.5]],
        exchange="coinbase",
        symbol="BTC/USD",
        timeframe="5m",
    )

    assert list(candles.columns) == MARKET_CANDLE_COLUMNS
    assert candles.loc[0, "timestamp"] == "2026-04-24T03:06:40+00:00"
    assert candles.loc[0, "exchange"] == "coinbase"
    assert candles.loc[0, "symbol"] == "BTC/USD"
    assert candles.loc[0, "open"] == 100.0


def test_normalize_ohlcv_rejects_malformed_rows() -> None:
    """Malformed CCXT rows are rejected before storage."""
    with pytest.raises(ValueError, match="Malformed OHLCV row"):
        normalize_ohlcv(
            raw_rows=[[1_777_000_000_000, 100, 110]],
            exchange="coinbase",
            symbol="BTC/USD",
            timeframe="5m",
        )


def test_normalize_ohlcv_rejects_non_finite_rows() -> None:
    """NaN or infinite numeric values are malformed API rows."""
    with pytest.raises(ValueError, match="non-finite"):
        normalize_ohlcv(
            raw_rows=[[1_777_000_000_000, 100, 110, 95, float("nan"), 12.5]],
            exchange="coinbase",
            symbol="BTC/USD",
            timeframe="5m",
        )


def test_fetch_ohlcv_success_uses_fake_ccxt_exchange(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful multi-symbol fetch returns live candles with metadata."""

    class FakeExchange:
        symbols = ["BTC/USD", "ETH/USD"]

        def __init__(self, config: dict[str, object]) -> None:
            self.config = config

        def load_markets(self) -> None:
            return None

        def fetch_ohlcv(
            self, symbol: str, timeframe: str, limit: int
        ) -> list[list[float]]:
            assert timeframe == "5m"
            assert limit == 2
            base = 1_777_000_000_000 if symbol == "BTC/USD" else 1_777_000_300_000
            return [
                [base, 100, 110, 95, 105, 12.5],
                [base + 300_000, 105, 112, 101, 108, 14.0],
            ]

    monkeypatch.setitem(sys.modules, "ccxt", SimpleNamespace(coinbase=FakeExchange))

    candles = fetch_ohlcv("coinbase", ["BTC/USD", "ETH/USD"], "5m", 2)

    assert len(candles) == 4
    assert candles.attrs["data_source"] == "live"
    assert candles.attrs["api_status"] == "ok"
    assert candles.attrs["exchange"] == "coinbase"
    assert candles["fetched_at"].nunique() == 1
    assert candles.attrs["latest_candle_timestamp"] == "2026-04-24T03:16:40+00:00"


def test_load_market_data_falls_back_on_exchange_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Exchange/API failures return deterministic sample fallback data."""

    class FailingExchange:
        symbols = ["BTC/USD"]

        def __init__(self, config: dict[str, object]) -> None:
            self.config = config

        def load_markets(self) -> None:
            return None

        def fetch_ohlcv(
            self, symbol: str, timeframe: str, limit: int
        ) -> list[list[float]]:
            raise TimeoutError("network timeout")

    fallback_path = tmp_path / "sample_market_candles.csv"
    generate_sample_market_candles(periods=3).to_csv(fallback_path, index=False)
    monkeypatch.setitem(sys.modules, "ccxt", SimpleNamespace(coinbase=FailingExchange))

    candles = load_market_data("coinbase", ["BTC/USD"], "5m", 3, str(fallback_path))

    assert len(candles) == 9
    assert candles.attrs["data_source"] == "sample"
    assert candles.attrs["api_status"] == "unavailable"
    assert "TimeoutError" in candles.attrs["fallback_reason"]
    assert candles.attrs["latest_candle_timestamp"] == "2026-05-23T00:00:00+00:00"
    assert candles.attrs["last_fetched_at"] == "2026-05-23T00:00:00+00:00"


def test_load_market_data_falls_back_on_empty_response(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Empty API responses are treated as unavailable data."""

    class EmptyExchange:
        symbols = ["BTC/USD"]

        def __init__(self, config: dict[str, object]) -> None:
            self.config = config

        def load_markets(self) -> None:
            return None

        def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
            return []

    fallback_path = tmp_path / "sample_market_candles.csv"
    generate_sample_market_candles(periods=2).to_csv(fallback_path, index=False)
    monkeypatch.setitem(sys.modules, "ccxt", SimpleNamespace(coinbase=EmptyExchange))

    candles = load_market_data("coinbase", ["BTC/USD"], "5m", 2, str(fallback_path))

    assert candles.attrs["data_source"] == "sample"
    assert "ValueError" in candles.attrs["fallback_reason"]


def test_load_market_data_falls_back_on_unsupported_exchange(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Unknown CCXT exchanges use fallback data instead of crashing."""
    fallback_path = tmp_path / "sample_market_candles.csv"
    generate_sample_market_candles(periods=1).to_csv(fallback_path, index=False)
    monkeypatch.setitem(sys.modules, "ccxt", SimpleNamespace())

    candles = load_market_data("missing_exchange", ["BTC/USD"], "5m", 1, str(fallback_path))

    assert len(candles) == 3
    assert candles.attrs["data_source"] == "sample"
    assert "Unsupported CCXT exchange" in candles.attrs["fallback_reason"]


def test_load_market_data_falls_back_on_unsupported_symbol(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Exchange symbol validation failures use fallback data."""

    class FakeExchange:
        symbols = ["ETH/USD"]

        def __init__(self, config: dict[str, object]) -> None:
            self.config = config

        def load_markets(self) -> None:
            return None

    fallback_path = tmp_path / "sample_market_candles.csv"
    generate_sample_market_candles(periods=1).to_csv(fallback_path, index=False)
    monkeypatch.setitem(sys.modules, "ccxt", SimpleNamespace(coinbase=FakeExchange))

    candles = load_market_data("coinbase", ["BTC/USD"], "5m", 1, str(fallback_path))

    assert candles.attrs["data_source"] == "sample"
    assert "Unsupported symbol" in candles.attrs["fallback_reason"]


def test_load_market_data_falls_back_on_rate_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Rate limit exceptions use fallback data."""

    class RateLimitExceeded(Exception):
        pass

    class RateLimitedExchange:
        symbols = ["BTC/USD"]

        def __init__(self, config: dict[str, object]) -> None:
            self.config = config

        def load_markets(self) -> None:
            return None

        def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
            raise RateLimitExceeded("too many requests")

    fallback_path = tmp_path / "sample_market_candles.csv"
    generate_sample_market_candles(periods=1).to_csv(fallback_path, index=False)
    monkeypatch.setitem(sys.modules, "ccxt", SimpleNamespace(coinbase=RateLimitedExchange))

    candles = load_market_data("coinbase", ["BTC/USD"], "5m", 1, str(fallback_path))

    assert candles.attrs["data_source"] == "sample"
    assert "RateLimitExceeded" in candles.attrs["fallback_reason"]


def test_load_market_data_falls_back_on_malformed_rows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Malformed API rows detected during normalization use fallback data."""

    class MalformedExchange:
        symbols = ["BTC/USD"]

        def __init__(self, config: dict[str, object]) -> None:
            self.config = config

        def load_markets(self) -> None:
            return None

        def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[list[object]]:
            return [[1_777_000_000_000, 100, 110, 95, "bad-close", 12.5]]

    fallback_path = tmp_path / "sample_market_candles.csv"
    generate_sample_market_candles(periods=1).to_csv(fallback_path, index=False)
    monkeypatch.setitem(sys.modules, "ccxt", SimpleNamespace(coinbase=MalformedExchange))

    candles = load_market_data("coinbase", ["BTC/USD"], "5m", 1, str(fallback_path))

    assert candles.attrs["data_source"] == "sample"
    assert "Malformed OHLCV row" in candles.attrs["fallback_reason"]


def test_load_market_data_regenerates_bad_fallback_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A malformed local fallback CSV is regenerated instead of crashing."""

    class FailingExchange:
        symbols = ["BTC/USD"]

        def __init__(self, config: dict[str, object]) -> None:
            self.config = config

        def load_markets(self) -> None:
            return None

        def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
            raise TimeoutError("network timeout")

    fallback_path = tmp_path / "sample_market_candles.csv"
    fallback_path.write_text("not,the,right,schema\n1,2,3,4\n", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "ccxt", SimpleNamespace(coinbase=FailingExchange))

    candles = load_market_data("coinbase", ["BTC/USD"], "5m", 1, str(fallback_path))

    assert list(candles.columns) == MARKET_CANDLE_COLUMNS
    assert len(candles) == 300
    assert candles.attrs["data_source"] == "sample"


def test_generate_sample_market_candles_is_deterministic() -> None:
    """The same seed produces identical fallback candles, including fetched_at."""
    first = generate_sample_market_candles(periods=3, seed=42)
    second = generate_sample_market_candles(periods=3, seed=42)

    pd.testing.assert_frame_equal(first, second)
    assert first["fetched_at"].nunique() == 1
    assert first["fetched_at"].iloc[0] == "2026-05-23T00:00:00+00:00"


def test_committed_sample_market_candles_are_schema_compatible() -> None:
    """The committed fallback CSV is non-empty and schema-compatible."""
    candles = pd.read_csv("data/sample_market_candles.csv")

    assert not candles.empty
    assert list(candles.columns) == MARKET_CANDLE_COLUMNS
