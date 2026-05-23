"""Pump-and-dump candidate detection over market candles."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.config.thresholds import (
    PUMP_RETURN_THRESHOLD,
    PUMP_WINDOW,
    REVERSAL_THRESHOLD,
    REVERSAL_WINDOW,
    ROLLING_WINDOW,
    VOLUME_Z_THRESHOLD,
)
from src.detection.severity import (
    make_dedup_key,
    pump_dump_score,
    severity_from_score,
)


ALERT_TYPE = "Pump-and-Dump Candidate"
VOLUME_SPIKE_ALERT_TYPE = "Volume Spike"
RECOMMENDED_FOLLOW_UP = "Review coordinated activity and prior volume alerts for the symbol."


def detect_pump_dump_candidates(
    market_candles: pd.DataFrame, existing_alerts: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Detect pump windows with volume confirmation and rapid reversal."""
    required_columns = {
        "exchange",
        "symbol",
        "timeframe",
        "timestamp",
        "close",
        "volume",
    }
    missing_columns = required_columns.difference(market_candles.columns)
    if missing_columns:
        raise ValueError(f"Market candles missing columns: {sorted(missing_columns)}")
    if market_candles.empty:
        return _empty_alerts()

    candles = market_candles.copy()
    candles["timestamp"] = pd.to_datetime(candles["timestamp"], utc=True)
    candles["close"] = pd.to_numeric(candles["close"], errors="coerce")
    candles["volume"] = pd.to_numeric(candles["volume"], errors="coerce")
    candles = candles.sort_values(["exchange", "symbol", "timeframe", "timestamp"])
    group_columns = ["exchange", "symbol", "timeframe"]
    candles["rolling_mean_volume"] = candles.groupby(group_columns)["volume"].transform(
        lambda series: series.shift(1).rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean()
    )
    candles["rolling_std_volume"] = candles.groupby(group_columns)["volume"].transform(
        lambda series: series.shift(1).rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).std()
    )
    candles["volume_z_score"] = (
        (candles["volume"] - candles["rolling_mean_volume"])
        / candles["rolling_std_volume"].replace(0, np.nan)
    )

    alerts: list[dict[str, Any]] = []
    for _, group in candles.groupby(group_columns, sort=False):
        group = group.reset_index(drop=True)
        for peak_index in range(PUMP_WINDOW, len(group) - REVERSAL_WINDOW):
            start_index = peak_index - PUMP_WINDOW
            start_close = float(group.loc[start_index, "close"])
            peak_close = float(group.loc[peak_index, "close"])
            if start_close == 0:
                continue
            pump_return = (peak_close - start_close) / start_close
            future = group.loc[peak_index + 1 : peak_index + REVERSAL_WINDOW].copy()
            if future.empty:
                continue
            reversal_index = int(future["close"].idxmin())
            reversal_close = float(group.loc[reversal_index, "close"])
            reversal_return = (reversal_close - peak_close) / peak_close
            volume_z_score = float(group.loc[peak_index, "volume_z_score"])
            if (
                pump_return >= PUMP_RETURN_THRESHOLD
                and volume_z_score > VOLUME_Z_THRESHOLD
                and reversal_return <= REVERSAL_THRESHOLD
            ):
                alerts.append(
                    _alert_from_window(
                        group.loc[start_index],
                        group.loc[peak_index],
                        group.loc[reversal_index],
                        pump_return,
                        reversal_return,
                        volume_z_score,
                        existing_alerts,
                    )
                )
    return pd.DataFrame(alerts)


def _alert_from_window(
    start_row: pd.Series,
    peak_row: pd.Series,
    reversal_row: pd.Series,
    pump_return: float,
    reversal_return: float,
    volume_z_score: float,
    existing_alerts: pd.DataFrame | None,
) -> dict[str, Any]:
    start_time = start_row["timestamp"].isoformat()
    peak_time = peak_row["timestamp"].isoformat()
    end_time = reversal_row["timestamp"].isoformat()
    symbol = str(peak_row["symbol"])
    multiple_rule_confirmed = _has_volume_spike(existing_alerts, symbol, start_time, end_time)
    score = pump_dump_score(
        pump_return=pump_return,
        volume_confirmed=True,
        reversal_confirmed=True,
        all_conditions_confirmed=True,
        multiple_rules_confirmed=multiple_rule_confirmed,
    )
    severity = severity_from_score(score)
    return {
        "alert_type": ALERT_TYPE,
        "severity": severity,
        "severity_score": score,
        "exchange": str(peak_row["exchange"]),
        "symbol": symbol,
        "start_time": start_time,
        "end_time": end_time,
        "account_id": None,
        "evidence_summary": (
            f"{symbol} rose {pump_return:.2%}, then reversed {reversal_return:.2%} "
            f"with volume z-score {volume_z_score:.2f}."
        ),
        "recommended_follow_up": RECOMMENDED_FOLLOW_UP,
        "dedup_key": make_dedup_key(ALERT_TYPE, symbol, start_time, end_time),
        "created_at": end_time,
        "evidence": [
            _evidence("pump_window_return", pump_return, PUMP_RETURN_THRESHOLD, ">=", "Return over pump window."),
            _evidence("peak_price", peak_row["close"], None, None, f"Peak candle at {peak_time}."),
            _evidence(
                "reversal_return",
                reversal_return,
                REVERSAL_THRESHOLD,
                "<=",
                "Return from peak to reversal low.",
            ),
            _evidence("volume_z_score", volume_z_score, VOLUME_Z_THRESHOLD, ">", "Peak candle volume z-score."),
        ],
    }


def _has_volume_spike(
    existing_alerts: pd.DataFrame | None, symbol: str, start_time: str, end_time: str
) -> bool:
    if existing_alerts is None or existing_alerts.empty:
        return False
    required_columns = {"alert_type", "symbol", "start_time", "end_time"}
    if not required_columns.issubset(existing_alerts.columns):
        return False
    alerts = existing_alerts.copy()
    alerts["start_time"] = pd.to_datetime(alerts["start_time"], utc=True)
    alerts["end_time"] = pd.to_datetime(alerts["end_time"], utc=True)
    window_start = pd.Timestamp(start_time)
    window_end = pd.Timestamp(end_time)
    overlaps = alerts[
        (alerts["alert_type"] == VOLUME_SPIKE_ALERT_TYPE)
        & (alerts["symbol"] == symbol)
        & (alerts["start_time"] <= window_end)
        & (alerts["end_time"] >= window_start)
    ]
    return not overlaps.empty


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
