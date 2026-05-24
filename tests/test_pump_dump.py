"""Pump-and-dump candidate detection tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from src.config.thresholds import PUMP_WINDOW, REVERSAL_WINDOW, ROLLING_WINDOW
from src.detection.pump_dump import detect_pump_dump_candidates


def pump_dump_candles(
    trigger: bool = True,
    include_volume_spike: bool = True,
    include_reversal: bool = True,
) -> pd.DataFrame:
    """Build candles with an optional pump, volume spike, and reversal."""
    start = datetime(2026, 5, 23, tzinfo=UTC)
    row_count = ROLLING_WINDOW + PUMP_WINDOW + REVERSAL_WINDOW + 2
    peak_index = ROLLING_WINDOW + PUMP_WINDOW
    rows = []
    for index in range(row_count):
        timestamp = start + timedelta(minutes=5 * index)
        close = 100.0
        volume = 100 + (index % 2)
        if trigger and index == peak_index:
            close = 106.0
            volume = 400.0 if include_volume_spike else 100.0
        elif trigger and not include_reversal and peak_index < index <= peak_index + REVERSAL_WINDOW:
            close = 106.0
        elif trigger and include_reversal and index == peak_index + 1:
            close = 102.0
        rows.append(
            {
                "exchange": "coinbase",
                "symbol": "SOL/USD",
                "timeframe": "5m",
                "timestamp": timestamp.isoformat(),
                "open": 100.0,
                "high": max(100.0, close),
                "low": min(100.0, close),
                "close": close,
                "volume": volume,
                "fetched_at": "2026-05-23T00:00:00+00:00",
            }
        )
    return pd.DataFrame(rows)


def test_detect_pump_dump_candidate_returns_alert() -> None:
    """A pump with volume confirmation and reversal triggers."""
    alerts = detect_pump_dump_candidates(pump_dump_candles())

    assert len(alerts) == 1
    alert = alerts.iloc[0]
    assert alert["alert_type"] == "Pump-and-Dump Candidate"
    assert alert["symbol"] == "SOL/USD"
    assert alert["severity_score"] == 55
    assert alert["severity"] == "Medium"
    assert alert["start_time"].startswith("2026-05-23T02:00:00")
    assert {item["metric_name"] for item in alert["evidence"]} == {
        "pump_window_return",
        "peak_price",
        "reversal_return",
        "volume_z_score",
    }


def test_detect_pump_dump_candidate_can_include_cross_rule_confirmation() -> None:
    """An overlapping volume alert raises severity through the central scorer."""
    existing_alerts = pd.DataFrame(
        [
            {
                "alert_type": "Volume Spike",
                "symbol": "SOL/USD",
                "start_time": "2026-05-23T02:15:00+00:00",
                "end_time": "2026-05-23T02:15:00+00:00",
            }
        ]
    )

    alerts = detect_pump_dump_candidates(pump_dump_candles(), existing_alerts)

    assert alerts.iloc[0]["severity_score"] == 80
    assert alerts.iloc[0]["severity"] == "High"


def test_detect_pump_dump_candidate_requires_all_conditions() -> None:
    """A flat series does not trigger."""
    alerts = detect_pump_dump_candidates(pump_dump_candles(trigger=False))

    assert alerts.empty


def test_detect_pump_dump_candidate_requires_reversal() -> None:
    """A pump and volume spike without a reversal does not trigger."""
    alerts = detect_pump_dump_candidates(pump_dump_candles(include_reversal=False))

    assert alerts.empty


def test_detect_pump_dump_candidate_requires_volume_confirmation() -> None:
    """A pump and reversal without volume confirmation does not trigger."""
    alerts = detect_pump_dump_candidates(pump_dump_candles(include_volume_spike=False))

    assert alerts.empty
