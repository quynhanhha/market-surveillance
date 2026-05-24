"""Price anomaly detection over market candles."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.config.thresholds import RETURN_Z_THRESHOLD, ROLLING_WINDOW
from src.detection.severity import (
    make_dedup_key,
    price_anomaly_score,
    severity_from_score,
)


ALERT_TYPE = "Price Anomaly"
RECOMMENDED_FOLLOW_UP = "Review news, liquidity, and related alerts for the anomalous candle."


def detect_price_anomalies(market_candles: pd.DataFrame) -> pd.DataFrame:
    """Detect candles whose return deviates from the previous rolling baseline."""
    required_columns = {
        "exchange",
        "symbol",
        "timeframe",
        "timestamp",
        "open",
        "close",
    }
    missing_columns = required_columns.difference(market_candles.columns)
    if missing_columns:
        raise ValueError(f"Market candles missing columns: {sorted(missing_columns)}")
    if market_candles.empty:
        return _empty_alerts()

    candles = market_candles.copy()
    candles["timestamp"] = pd.to_datetime(candles["timestamp"], utc=True)
    candles["open"] = pd.to_numeric(candles["open"], errors="coerce")
    candles["close"] = pd.to_numeric(candles["close"], errors="coerce")
    candles = candles[
        np.isfinite(candles["open"])
        & np.isfinite(candles["close"])
        & (candles["open"] > 0)
    ].copy()
    candles = candles.sort_values(["exchange", "symbol", "timeframe", "timestamp"])
    candles["return"] = (candles["close"] - candles["open"]) / candles["open"]

    group_columns = ["exchange", "symbol", "timeframe"]
    grouped_returns = candles.groupby(group_columns)["return"]
    candles["rolling_mean_return"] = grouped_returns.transform(
        lambda series: series.shift(1).rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean()
    )
    candles["rolling_std_return"] = grouped_returns.transform(
        lambda series: series.shift(1).rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).std()
    )
    candles["return_z_score"] = (
        (candles["return"] - candles["rolling_mean_return"])
        / candles["rolling_std_return"].replace(0, np.nan)
    )

    triggered = candles[
        (candles["return_z_score"].abs() > RETURN_Z_THRESHOLD)
        & candles["return_z_score"].notna()
    ]
    alerts = [_alert_from_row(row) for _, row in triggered.iterrows()]
    return pd.DataFrame(alerts)


def _alert_from_row(row: pd.Series) -> dict[str, Any]:
    start_time = row["timestamp"].isoformat()
    end_time = start_time
    score = price_anomaly_score(float(row["return_z_score"]))
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
            f"{symbol} return {row['return']:.2%} had "
            f"z-score {row['return_z_score']:.2f}."
        ),
        "recommended_follow_up": RECOMMENDED_FOLLOW_UP,
        "dedup_key": make_dedup_key(ALERT_TYPE, symbol, start_time, end_time),
        "created_at": end_time,
        "evidence": [
            _evidence("return_percentage", row["return"] * 100, RETURN_Z_THRESHOLD, "abs >", "Candle return percentage."),
            _evidence(
                "rolling_average_return",
                row["rolling_mean_return"],
                None,
                None,
                "Previous rolling average return.",
            ),
            _evidence(
                "return_z_score",
                row["return_z_score"],
                RETURN_Z_THRESHOLD,
                "abs >",
                "Return z-score over previous rolling window.",
            ),
            _evidence("open_price", row["open"], None, None, "Candle open price."),
            _evidence("close_price", row["close"], None, None, "Candle close price."),
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
