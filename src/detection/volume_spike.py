"""Volume spike detection over market candles."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.config.thresholds import (
    MIN_VOLUME_MULTIPLIER,
    ROLLING_WINDOW,
    VOLUME_Z_THRESHOLD,
)
from src.detection.severity import (
    make_dedup_key,
    severity_from_score,
    volume_spike_score,
)


ALERT_TYPE = "Volume Spike"
RECOMMENDED_FOLLOW_UP = "Review market context and related account activity for the spike window."


def detect_volume_spikes(market_candles: pd.DataFrame) -> pd.DataFrame:
    """Detect candles whose volume exceeds the previous rolling baseline."""
    required_columns = {
        "exchange",
        "symbol",
        "timeframe",
        "timestamp",
        "volume",
    }
    missing_columns = required_columns.difference(market_candles.columns)
    if missing_columns:
        raise ValueError(f"Market candles missing columns: {sorted(missing_columns)}")
    if market_candles.empty:
        return _empty_alerts()

    candles = market_candles.copy()
    candles["timestamp"] = pd.to_datetime(candles["timestamp"], utc=True)
    candles["volume"] = pd.to_numeric(candles["volume"], errors="coerce")
    candles = candles.sort_values(["exchange", "symbol", "timeframe", "timestamp"])
    group_columns = ["exchange", "symbol", "timeframe"]
    grouped_volume = candles.groupby(group_columns)["volume"]
    candles["rolling_mean_volume"] = grouped_volume.transform(
        lambda series: series.shift(1).rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean()
    )
    candles["rolling_std_volume"] = grouped_volume.transform(
        lambda series: series.shift(1).rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).std()
    )
    candles["volume_z_score"] = (
        (candles["volume"] - candles["rolling_mean_volume"])
        / candles["rolling_std_volume"].replace(0, np.nan)
    )
    candles["volume_multiplier"] = candles["volume"] / candles["rolling_mean_volume"]

    triggered = candles[
        (candles["volume_z_score"] > VOLUME_Z_THRESHOLD)
        & candles["volume_z_score"].notna()
    ]
    alerts = [_alert_from_row(row) for _, row in triggered.iterrows()]
    return pd.DataFrame(alerts)


def _alert_from_row(row: pd.Series) -> dict[str, Any]:
    start_time = row["timestamp"].isoformat()
    end_time = start_time
    score = volume_spike_score(
        float(row["volume_z_score"]),
        bool(row["volume_multiplier"] >= MIN_VOLUME_MULTIPLIER),
    )
    severity = severity_from_score(score)
    symbol = str(row["symbol"])
    return {
        "alert_type": ALERT_TYPE,
        "severity": severity,
        "severity_score": score,
        "exchange": str(row["exchange"]),
        "symbol": symbol,
        "start_time": start_time,
        "end_time": end_time,
        "account_id": None,
        "evidence_summary": (
            f"{symbol} volume {row['volume']:.4f} was "
            f"{row['volume_z_score']:.2f} standard deviations above baseline."
        ),
        "recommended_follow_up": RECOMMENDED_FOLLOW_UP,
        "dedup_key": make_dedup_key(ALERT_TYPE, symbol, start_time, end_time),
        "created_at": end_time,
        "evidence": [
            _evidence("current_volume", row["volume"], VOLUME_Z_THRESHOLD, ">", "Current candle volume."),
            _evidence(
                "rolling_mean_volume",
                row["rolling_mean_volume"],
                None,
                None,
                "Previous rolling mean volume.",
            ),
            _evidence(
                "volume_z_score",
                row["volume_z_score"],
                VOLUME_Z_THRESHOLD,
                ">",
                "Volume z-score over previous rolling window.",
            ),
            _evidence(
                "volume_multiplier",
                row["volume_multiplier"],
                MIN_VOLUME_MULTIPLIER,
                ">=",
                "Current volume divided by rolling mean volume.",
            ),
        ],
    }


def _evidence(
    metric_name: str,
    metric_value: object,
    threshold_value: object,
    comparison_operator: str | None,
    explanation: str,
) -> dict[str, Any]:
    return {
        "metric_name": metric_name,
        "metric_value": float(metric_value) if pd.notna(metric_value) else None,
        "threshold_value": float(threshold_value) if threshold_value is not None else None,
        "comparison_operator": comparison_operator,
        "explanation": explanation,
    }


def _empty_alerts() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "alert_type",
            "severity",
            "severity_score",
            "exchange",
            "symbol",
            "start_time",
            "end_time",
            "account_id",
            "evidence_summary",
            "recommended_follow_up",
            "dedup_key",
            "created_at",
            "evidence",
        ]
    )
