"""Volume spike detection tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from src.config.thresholds import ROLLING_WINDOW
from src.detection.volume_spike import detect_volume_spikes


def market_candles_with_volume(last_volume: float) -> pd.DataFrame:
    """Build a stable market candle series with one configurable final volume."""
    start = datetime(2026, 5, 23, tzinfo=UTC)
    rows = []
    for index in range(ROLLING_WINDOW + 1):
        timestamp = start + timedelta(minutes=5 * index)
        volume = 100 + (index % 2) if index < ROLLING_WINDOW else last_volume
        rows.append(
            {
                "exchange": "coinbase",
                "symbol": "BTC/USD",
                "timeframe": "5m",
                "timestamp": timestamp.isoformat(),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": volume,
                "fetched_at": "2026-05-23T00:00:00+00:00",
            }
        )
    return pd.DataFrame(rows)


def test_detect_volume_spike_returns_alert_with_evidence() -> None:
    """A high-volume candle produces an alert-ready row."""
    alerts = detect_volume_spikes(market_candles_with_volume(400))

    assert len(alerts) == 1
    alert = alerts.iloc[0]
    assert alert["alert_type"] == "Volume Spike"
    assert alert["symbol"] == "BTC/USD"
    assert alert["severity_score"] >= 55
    assert alert["severity"] == "Medium"
    assert alert["start_time"] == alert["end_time"]
    assert alert["start_time"].startswith("2026-05-23T02:00:00")
    assert {item["metric_name"] for item in alert["evidence"]} == {
        "current_volume",
        "rolling_mean_volume",
        "volume_z_score",
        "volume_multiplier",
    }


def test_detect_volume_spike_ignores_below_threshold_volume() -> None:
    """A normal volume candle does not trigger."""
    alerts = detect_volume_spikes(market_candles_with_volume(102))

    assert alerts.empty
