"""Markdown daily surveillance summary generation."""

from __future__ import annotations

import pandas as pd


def generate_daily_summary(
    alerts: pd.DataFrame, candles: pd.DataFrame, metadata: dict[str, str]
) -> str:
    """Generate a daily Markdown surveillance report."""
    data_source = metadata.get("data_source", "unknown")
    symbols = sorted(candles["symbol"].dropna().unique()) if "symbol" in candles else []
    severity_counts = _counts(alerts, "severity")
    type_counts = _counts(alerts, "alert_type")
    highest = alerts.sort_values("severity_score", ascending=False).head(5) if not alerts.empty else alerts
    abnormal = (
        candles.assign(
            absolute_return=lambda frame: (
                (pd.to_numeric(frame["close"], errors="coerce") - pd.to_numeric(frame["open"], errors="coerce"))
                / pd.to_numeric(frame["open"], errors="coerce")
            ).abs()
        )
        .sort_values("absolute_return", ascending=False)
        .head(5)
        if not candles.empty and {"open", "close"}.issubset(candles.columns)
        else pd.DataFrame()
    )

    lines = [
        "# Daily Surveillance Report",
        "",
        f"- Data source: {data_source}",
        f"- API status: {metadata.get('api_status', 'unknown')}",
        f"- Last fetched: {metadata.get('last_fetched_at', '')}",
        f"- Symbols monitored: {', '.join(symbols) if symbols else 'None'}",
        f"- Total alerts: {len(alerts)}",
        "",
        "## Severity Summary",
        _format_counts(severity_counts),
        "",
        "## Alert Type Summary",
        _format_counts(type_counts),
        "",
        "## Highest Severity Alerts",
        _format_alerts(highest),
        "",
        "## Abnormal Movements",
        _format_movements(abnormal),
        "",
        "## Synthetic Summary",
        _format_counts(_counts(alerts[alerts["exchange"].isna()] if "exchange" in alerts else alerts, "alert_type")),
        "",
        "## Limitations",
        "Public market APIs do not expose private account identifiers or full order lifecycle records. Account-level scenarios in this prototype are deterministic synthetic data, not real accounts or transactions. SQLite storage is ephemeral in the deployed demo.",
        "",
        "## Follow-Up",
        "Review high severity alerts first, compare related alerts in the same symbol window, and document disposition before escalation.",
    ]
    return "\n".join(lines)


def _counts(frame: pd.DataFrame, column: str) -> pd.Series:
    if frame.empty or column not in frame:
        return pd.Series(dtype="int64")
    return frame[column].fillna("Unknown").value_counts()


def _format_counts(counts: pd.Series) -> str:
    if counts.empty:
        return "No rows."
    return "\n".join(f"- {label}: {count}" for label, count in counts.items())


def _format_alerts(alerts: pd.DataFrame) -> str:
    if alerts.empty:
        return "No alerts."
    return "\n".join(
        f"- #{row.alert_id}: {row.alert_type} | {row.symbol or 'N/A'} | "
        f"{row.severity} ({row.severity_score}) | {row.status}"
        for row in alerts.itertuples()
    )


def _format_movements(candles: pd.DataFrame) -> str:
    if candles.empty:
        return "No candle movement data available."
    return "\n".join(
        f"- {row.symbol}: {row.absolute_return:.2%} at {row.timestamp}"
        for row in candles.itertuples()
    )
