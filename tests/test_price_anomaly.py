"""Price anomaly detection tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from src.config.thresholds import ROLLING_WINDOW
from src.detection.price_anomaly import detect_price_anomalies


def market_candles_with_final_return(final_close: float) -> pd.DataFrame:
    """Build a market candle series with one configurable final close."""
    start = datetime(2026, 5, 23, tzinfo=UTC)
    rows = []
    for index in range(ROLLING_WINDOW + 1):
        timestamp = start + timedelta(minutes=5 * index)
        close = 101.0 if index % 2 == 0 else 99.5
        if index == ROLLING_WINDOW:
            close = final_close
        rows.append(
            {
                "exchange": "coinbase",
                "symbol": "ETH/USD",
                "timeframe": "5m",
                "timestamp": timestamp.isoformat(),
                "open": 100.0,
                "high": max(100.0, close),
                "low": min(100.0, close),
                "close": close,
                "volume": 100.0,
                "fetched_at": "2026-05-23T00:00:00+00:00",
            }
        )
    return pd.DataFrame(rows)


def test_detect_price_anomaly_returns_alert_with_evidence() -> None:
    """An abnormal return produces an alert-ready row."""
    alerts = detect_price_anomalies(market_candles_with_final_return(115.0))

    assert len(alerts) == 1
    alert = alerts.iloc[0]
    assert alert["alert_type"] == "Price Anomaly"
    assert alert["symbol"] == "ETH/USD"
    assert alert["severity_score"] == 40
    assert alert["severity"] == "Low"
    assert alert["start_time"] == alert["end_time"]
    assert {item["metric_name"] for item in alert["evidence"]} == {
        "return_percentage",
        "rolling_average_return",
        "return_z_score",
        "open_price",
        "close_price",
    }


def test_detect_price_anomaly_handles_extreme_negative_return() -> None:
    """A large negative return also triggers through absolute z-score."""
    alerts = detect_price_anomalies(market_candles_with_final_return(85.0))

    assert len(alerts) == 1
    assert alerts.iloc[0]["severity_score"] == 40
    assert alerts.iloc[0]["severity"] == "Low"


def test_detect_price_anomaly_ignores_normal_return() -> None:
    """A normal return does not trigger."""
    alerts = detect_price_anomalies(market_candles_with_final_return(100.5))

    assert alerts.empty


def test_detect_price_anomaly_handles_zero_and_nan_safely() -> None:
    """Bad current candle prices do not create false alerts."""
    zero_open = market_candles_with_final_return(115.0)
    zero_open.loc[ROLLING_WINDOW, "open"] = 0.0
    nan_close = market_candles_with_final_return(115.0)
    nan_close.loc[ROLLING_WINDOW, "close"] = pd.NA

    assert detect_price_anomalies(zero_open).empty
    assert detect_price_anomalies(nan_close).empty
