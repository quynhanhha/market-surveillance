"""Streamlit page layouts for the surveillance dashboard."""

from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from src.reporting.case_report import generate_case_report
from src.reporting.daily_summary import generate_daily_summary
from src.storage.repositories import fetch_alert_evidence, update_alert_status
from src.ui.charts import (
    alert_counts_by_day,
    price_volume_dual_axis_chart,
    selected_symbol_candles,
    severity_bar_chart,
    severity_counts,
    top_price_movement_symbols,
    top_volume_symbols,
)
from src.ui.components import ALERT_STATUSES, alert_table, render_alert_table


PRICE_ALERT = "Price Anomaly"
VOLUME_ALERT = "Volume Spike"
PUMP_ALERT = "Pump-and-Dump Candidate"
WASH_ALERT = "Synthetic Wash Trading Pattern"
SPOOF_ALERT = "Synthetic Spoofing/Layering Pattern"


def overview_page(alerts: pd.DataFrame, candles: pd.DataFrame, selected_symbol: str) -> None:
    """Render the dashboard overview."""
    st.title("Overview")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Total Alerts", f"{len(alerts):,}")
    metric_columns[1].metric("High+ Severity", f"{alerts[alerts['severity'].isin(['High', 'Critical'])].shape[0] if not alerts.empty else 0:,}")
    metric_columns[2].metric("Symbols", f"{candles['symbol'].nunique() if not candles.empty else 0:,}")
    metric_columns[3].metric("Candles", f"{len(candles):,}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Alerts by Type")
        chart_data = alert_counts_by_day(alerts)
        if chart_data.empty:
            st.info("No alerts in the selected filters.")
        else:
            st.bar_chart(chart_data, x="date", y="count", color="alert_type")
    with col_b:
        st.subheader("Severity")
        sev = severity_counts(alerts)
        if sev.empty:
            st.info("No severity rows.")
        else:
            st.altair_chart(severity_bar_chart(sev), use_container_width=True)

    st.subheader("Selected Symbol Price / Volume")
    chart_symbols = _available_symbols(candles)
    if not chart_symbols:
        st.info("No candles are available for charting.")
    else:
        for symbol, tab in zip(chart_symbols, st.tabs(chart_symbols), strict=True):
            with tab:
                symbol_candles = selected_symbol_candles(candles, symbol)
                if symbol_candles.empty:
                    st.info(f"No candles for {symbol}.")
                else:
                    st.plotly_chart(
                        price_volume_dual_axis_chart(symbol_candles, symbol),
                        use_container_width=True,
                        config={"scrollZoom": True},
                    )

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Top Abnormal-Volume Symbols")
        st.dataframe(top_volume_symbols(candles), use_container_width=True, hide_index=True)
    with col_d:
        st.subheader("Top Price-Movement Symbols")
        st.dataframe(top_price_movement_symbols(candles), use_container_width=True, hide_index=True)

    render_alert_table(alerts.head(20), "Latest Alerts")


def market_anomalies_page(alerts: pd.DataFrame) -> None:
    """Render market anomaly alert tables."""
    st.title("Market Anomalies")
    render_alert_table(alerts[alerts["alert_type"] == PRICE_ALERT], "Price Anomalies")
    render_alert_table(alerts[alerts["alert_type"] == VOLUME_ALERT], "Volume Spikes")
    render_alert_table(alerts[alerts["alert_type"] == PUMP_ALERT], "Pump-and-Dump Candidates")


def synthetic_cases_page(
    conn: sqlite3.Connection, alerts: pd.DataFrame, account_links: pd.DataFrame
) -> None:
    """Render synthetic surveillance case tables and status controls."""
    st.title("Synthetic Surveillance Cases")
    synthetic = alerts[alerts["alert_type"].isin([WASH_ALERT, SPOOF_ALERT])]
    render_alert_table(synthetic[synthetic["alert_type"] == WASH_ALERT], "Wash-Trading Cases")
    render_alert_table(synthetic[synthetic["alert_type"] == SPOOF_ALERT], "Spoofing / Layering Cases")

    st.subheader("Linked Accounts")
    st.dataframe(account_links, use_container_width=True, hide_index=True)

    st.subheader("Case Status Update")
    _status_controls(conn, synthetic)


def alert_detail_page(
    conn: sqlite3.Connection, alerts: pd.DataFrame, candles: pd.DataFrame
) -> None:
    """Render one alert investigation detail view."""
    st.title("Alert Detail")
    if alerts.empty:
        st.info("No alerts match the selected filters.")
        return
    options = {
        f"#{row.alert_id} | {row.alert_type} | {row.symbol or row.account_id} | {row.severity_score}": row.alert_id
        for row in alerts.itertuples()
    }
    selected_label = st.selectbox("Alert", list(options))
    alert_id = int(options[selected_label])
    alert = alerts[alerts["alert_id"] == alert_id].iloc[0]
    evidence = fetch_alert_evidence(conn, alert_id)

    cols = st.columns(5)
    cols[0].metric("Severity", str(alert["severity"]))
    cols[1].metric("Severity Score", str(alert["severity_score"]))
    cols[2].metric("Status", str(alert["status"]))
    cols[3].metric("Symbol", str(alert.get("symbol") or "N/A"))
    cols[4].metric("Alert ID", str(alert_id))
    st.caption(f"Window: {alert['start_time']} to {alert['end_time']}")
    st.write(alert["evidence_summary"])
    st.subheader("Evidence")
    st.dataframe(evidence, use_container_width=True, hide_index=True)

    st.subheader("Alert Window")
    window = _alert_window_candles(candles, alert)
    if window.empty:
        st.info("No market candles are available for this alert window.")
    else:
        st.line_chart(window.set_index("timestamp")[["close", "volume"]])

    st.subheader("Recommended Follow-Up")
    st.write(alert.get("recommended_follow_up") or "Review context and document disposition.")
    _status_controls(conn, alerts[alerts["alert_id"] == alert_id])

    report = generate_case_report(alert, evidence)
    st.subheader("Generated Case Note")
    st.text_area("Case report Markdown", value=report, height=320)
    st.download_button("Download Markdown", report, file_name=f"case_alert_{alert_id}.md")


def daily_report_page(
    alerts: pd.DataFrame, candles: pd.DataFrame, metadata: dict[str, str]
) -> None:
    """Render the daily Markdown report."""
    st.title("Daily Report")
    report = generate_daily_summary(alerts, candles, metadata)
    st.text_area("Daily report Markdown", value=report, height=520)
    st.download_button("Download Daily Report", report, file_name="daily_surveillance_report.md")


def methodology_page() -> None:
    """Render methodology and limitations."""
    st.title("Methodology & Limitations")
    st.markdown(
        """
Public exchange APIs provide market-level OHLCV data, not private account identifiers or full order lifecycle records. This dashboard therefore separates real public market monitoring from deterministic synthetic account-level scenarios.

Rule thresholds are centralized in `src/config/thresholds.py`, severity scoring is centralized in `src/detection/severity.py`, and alert persistence uses a deduplication key over alert type, symbol, candle window, and account where available.

The deployed SQLite database is ephemeral for the prototype. Refreshing or redeploying can rebuild sample state from committed data.

Alerts are surveillance leads only. They are not accusations, not financial advice, and may include false positives caused by liquidity, market news, exchange outages, or sample-data constraints.
        """
    )


def build_overview_summary(alerts: pd.DataFrame) -> dict[str, pd.DataFrame | int]:
    """Return overview data for tests and page rendering."""
    return {
        "total_alerts": len(alerts),
        "by_severity": severity_counts(alerts),
        "by_type": alerts.groupby("alert_type").size().reset_index(name="count")
        if not alerts.empty
        else pd.DataFrame(columns=["alert_type", "count"]),
    }


def market_anomaly_tables(alerts: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return market anomaly tables with standard alert columns."""
    return {
        "price": alert_table(alerts[alerts["alert_type"] == PRICE_ALERT]),
        "volume": alert_table(alerts[alerts["alert_type"] == VOLUME_ALERT]),
        "pump_dump": alert_table(alerts[alerts["alert_type"] == PUMP_ALERT]),
    }


def _available_symbols(candles: pd.DataFrame) -> list[str]:
    if candles.empty or "symbol" not in candles:
        return []
    return sorted(candles["symbol"].dropna().astype(str).unique())


def _status_controls(conn: sqlite3.Connection, alerts: pd.DataFrame) -> None:
    if alerts.empty:
        st.info("No eligible cases in the selected filters.")
        return
    alert_ids = alerts["alert_id"].astype(int).tolist()
    selected_alert_id = st.selectbox("Alert ID", alert_ids, key=f"status_alert_{id(alerts)}")
    selected_status = st.selectbox("New Status", ALERT_STATUSES, key=f"status_value_{id(alerts)}")
    if st.button("Update Status", key=f"status_button_{id(alerts)}"):
        update_alert_status(conn, int(selected_alert_id), selected_status)
        st.success(f"Alert {selected_alert_id} updated to {selected_status}.")
        st.rerun()


def _alert_window_candles(candles: pd.DataFrame, alert: pd.Series) -> pd.DataFrame:
    if candles.empty or pd.isna(alert.get("symbol")):
        return pd.DataFrame()
    frame = candles[candles["symbol"] == alert["symbol"]].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    start = pd.Timestamp(alert["start_time"]) - pd.Timedelta(minutes=30)
    end = pd.Timestamp(alert["end_time"]) + pd.Timedelta(minutes=30)
    return frame[(frame["timestamp"] >= start) & (frame["timestamp"] <= end)].sort_values("timestamp")
