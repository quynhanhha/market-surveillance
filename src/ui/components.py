"""Reusable Streamlit UI components and dataframe filters."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

import pandas as pd
import streamlit as st


ALERT_TABLE_COLUMNS = [
    "alert_id",
    "alert_type",
    "severity",
    "severity_score",
    "status",
    "exchange",
    "symbol",
    "account_id",
    "start_time",
    "end_time",
    "evidence_summary",
]
ALERT_STATUSES = ["New", "Under Review", "Escalated", "Closed"]
SEVERITIES = ["Low", "Medium", "High", "Critical"]


def render_sidebar(
    candles: pd.DataFrame, metadata: dict[str, str], alerts: pd.DataFrame
) -> dict[str, Any]:
    """Render global controls and data status."""
    st.sidebar.title("Surveillance")
    page = st.sidebar.radio(
        "Page",
        [
            "Overview",
            "Market Anomalies",
            "Synthetic Surveillance Cases",
            "Alert Detail",
            "Daily Report",
            "Methodology & Limitations",
        ],
    )
    exchanges = _options(candles, "exchange", alerts)
    symbols = _options(candles, "symbol", alerts)
    timeframes = _options(candles, "timeframe")
    selected_exchange = st.sidebar.selectbox("Exchange", exchanges)
    selected_symbol = st.sidebar.selectbox("Symbol", symbols)
    selected_timeframe = st.sidebar.selectbox("Timeframe", timeframes)
    severity = st.sidebar.multiselect("Severity", SEVERITIES, default=SEVERITIES)
    status = st.sidebar.multiselect("Alert Status", ALERT_STATUSES, default=ALERT_STATUSES)
    start_date, end_date = _date_bounds(candles, alerts)
    selected_dates = st.sidebar.date_input("Date Range", value=(start_date, end_date))
    refresh = st.sidebar.button("Refresh Data")
    auto_refresh = st.sidebar.toggle("Auto-refresh every 60s", value=False)

    st.sidebar.divider()
    st.sidebar.subheader("Data Status")
    st.sidebar.caption(f"Source: {metadata.get('data_source', 'unknown')}")
    st.sidebar.caption(f"API status: {metadata.get('api_status', 'unknown')}")
    st.sidebar.caption(f"Last fetched: {metadata.get('last_fetched_at', '')}")
    st.sidebar.caption(f"Candles loaded: {len(candles):,}")
    if reason := metadata.get("fallback_reason"):
        st.sidebar.caption(f"Fallback reason: {reason}")

    start_dt, end_dt = _selected_date_range(selected_dates)
    return {
        "page": page,
        "exchange": selected_exchange,
        "symbol": selected_symbol,
        "timeframe": selected_timeframe,
        "severity": severity,
        "status": status,
        "start_time": start_dt,
        "end_time": end_dt,
        "refresh": refresh,
        "auto_refresh": auto_refresh,
    }


def filter_alerts(alerts: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    """Apply global alert filters."""
    if alerts.empty:
        return alerts
    frame = alerts.copy()
    if filters.get("exchange") not in (None, "All") and "exchange" in frame:
        frame = frame[(frame["exchange"] == filters["exchange"]) | frame["exchange"].isna()]
    if filters.get("symbol") not in (None, "All") and "symbol" in frame:
        frame = frame[frame["symbol"] == filters["symbol"]]
    if severities := filters.get("severity"):
        frame = frame[frame["severity"].isin(severities)]
    if statuses := filters.get("status"):
        frame = frame[frame["status"].isin(statuses)]
    if filters.get("start_time"):
        frame = frame[pd.to_datetime(frame["end_time"], utc=True) >= _utc_timestamp(filters["start_time"])]
    if filters.get("end_time"):
        frame = frame[pd.to_datetime(frame["start_time"], utc=True) <= _utc_timestamp(filters["end_time"])]
    return frame


def filter_candles(candles: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    """Apply global candle filters."""
    if candles.empty:
        return candles
    frame = candles.copy()
    for column in ("exchange", "symbol", "timeframe"):
        if filters.get(column) not in (None, "All") and column in frame:
            frame = frame[frame[column] == filters[column]]
    if filters.get("start_time"):
        frame = frame[pd.to_datetime(frame["timestamp"], utc=True) >= _utc_timestamp(filters["start_time"])]
    if filters.get("end_time"):
        frame = frame[pd.to_datetime(frame["timestamp"], utc=True) <= _utc_timestamp(filters["end_time"])]
    return frame


def alert_table(alerts: pd.DataFrame) -> pd.DataFrame:
    """Return alert rows with required display columns, including severity_score."""
    columns = [column for column in ALERT_TABLE_COLUMNS if column in alerts.columns]
    return alerts[columns].copy() if columns else pd.DataFrame(columns=ALERT_TABLE_COLUMNS)


def render_alert_table(alerts: pd.DataFrame, label: str) -> None:
    """Render a standard alert table."""
    st.subheader(label)
    st.dataframe(alert_table(alerts), use_container_width=True, hide_index=True)


def _options(
    frame: pd.DataFrame, column: str, secondary: pd.DataFrame | None = None
) -> list[str]:
    values: set[str] = set()
    if not frame.empty and column in frame:
        values.update(str(value) for value in frame[column].dropna().unique())
    if secondary is not None and not secondary.empty and column in secondary:
        values.update(str(value) for value in secondary[column].dropna().unique())
    return ["All", *sorted(values)]


def _date_bounds(candles: pd.DataFrame, alerts: pd.DataFrame) -> tuple[date, date]:
    timestamps: list[pd.Timestamp] = []
    for frame, column in ((candles, "timestamp"), (alerts, "start_time"), (alerts, "end_time")):
        if not frame.empty and column in frame:
            timestamps.extend(pd.to_datetime(frame[column], utc=True).dropna().tolist())
    if not timestamps:
        today = datetime.now().date()
        return today, today
    return min(timestamps).date(), max(timestamps).date()


def _selected_date_range(value: Any) -> tuple[datetime | None, datetime | None]:
    if not isinstance(value, tuple) or len(value) != 2:
        return None, None
    start, end = value
    return datetime.combine(start, time.min), datetime.combine(end, time.max)


def _utc_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")
