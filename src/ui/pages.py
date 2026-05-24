"""Streamlit page layouts for the surveillance dashboard."""

from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from src.reporting.case_report import case_report_filename, generate_case_report_pdf
from src.reporting.daily_summary import (
    alert_csv_filename,
    alerts_to_csv,
    build_daily_report_summary,
    daily_alerts_csv_filename,
    generate_daily_report_pdf,
)
from src.storage.repositories import fetch_alert_evidence, update_alert_status
from src.ui.charts import (
    alert_counts_by_day,
    alert_type_bar_chart,
    price_volume_dual_axis_chart,
    selected_symbol_candles,
    severity_bar_chart,
    severity_counts,
    top_price_movement_symbols,
    top_volume_symbols,
)
from src.ui.components import ALERT_STATUSES, alert_table, format_dataframe_for_display


PRICE_ALERT = "Price Anomaly"
VOLUME_ALERT = "Volume Spike"
PUMP_ALERT = "Pump-and-Dump Candidate"
WASH_ALERT = "Synthetic Wash Trading Pattern"
SPOOF_ALERT = "Synthetic Spoofing/Layering Pattern"
GENERIC_EMPTY_TABLE_MESSAGE = "No data available for the current filters."
SEVERITY_COLORS = {
    "Critical": {"bg": "rgba(139, 0, 0, 0.25)", "text": "#8B0000"},
    "High": {"bg": "rgba(255, 107, 107, 0.2)", "text": "#cc3300"},
    "Medium": {"bg": "rgba(255, 179, 71, 0.2)", "text": "#b35900"},
    "Low": {"bg": "rgba(74, 158, 255, 0.2)", "text": "#1a5fa8"},
}
TABLE_HEADER_STYLE = """
<style>
table {
    width: 100% !important;
    table-layout: fixed !important;
    word-wrap: break-word !important;
}
td, th {
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 200px !important;
    white-space: normal !important;
}
thead th {
    font-weight: bold !important;
    text-align: center !important;
    white-space: nowrap !important;
    word-break: keep-all !important;
    overflow-wrap: normal !important;
}
</style>
"""
TABLE_DISPLAY_COLUMNS = {
    "alert_id": "ID",
    "alert_type": "Type",
    "severity": "Severity",
    "severity_score": "Score",
    "status": "Status",
    "exchange": "Exchange",
    "symbol": "Symbol",
    "account_id": "Account",
    "start_time": "Start",
    "end_time": "End",
    "evidence_summary": "Summary",
    "metric_name": "Metric",
    "metric_value": "Value",
    "threshold_value": "Threshold",
    "comparison_operator": "Operator",
    "explanation": "Explanation",
    "trade_count": "Trades",
    "notional_value": "Notional",
    "link_confidence": "Confidence",
    "absolute_return": "Return",
    "volume": "Volume",
}
EMPTY_TABLE_MESSAGES = {
    "Pump-and-Dump Candidates": (
        "No pump-and-dump candidates detected in the current monitoring window. "
        "This rule requires a 5%+ price increase within 3 candles followed by a 3%+ "
        "reversal within 6 candles. No symbols exceeded these thresholds in today's "
        "data, consistent with normal market conditions."
    ),
    "Spoofing/Layering Cases": (
        "No spoofing/layering patterns detected in the current synthetic dataset. "
        "This rule requires repeated large order cancellations followed by opposite-side "
        "trades within 180 seconds."
    ),
    "Wash Trading Cases": "No wash trading patterns detected.",
    "Price Anomalies": "No price anomalies detected in the current monitoring window.",
    "Volume Spikes": "No volume spikes detected in the current monitoring window.",
    "Latest Alerts": "No alerts generated yet. Refresh market data to run detection.",
}


def overview_page(alerts: pd.DataFrame, candles: pd.DataFrame, selected_symbol: str) -> None:
    """Render the dashboard overview."""
    st.markdown(
        """
    <script>
        const main = window.parent.document.querySelector(
            'section.main'
        );
        if (main) {
            main.scrollTo(0, 0);
        }
    </script>
    """,
        unsafe_allow_html=True,
    )
    _apply_table_header_styles()
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
            st.altair_chart(alert_type_bar_chart(chart_data), use_container_width=True)
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
                        key=f"price_volume_chart_{symbol}",
                    )

    col_c, col_d = st.columns(2)
    with col_c:
        _render_centered_overview_table(
            "Top Abnormal-Volume Symbols",
            _format_top_volume_table(top_volume_symbols(candles)),
        )
    with col_d:
        _render_centered_overview_table(
            "Top Price-Movement Symbols",
            _format_top_price_movement_table(top_price_movement_symbols(candles)),
        )

    _render_alert_table(alerts.head(20), "Latest Alerts")


def market_anomalies_page(alerts: pd.DataFrame) -> None:
    """Render market anomaly alert tables."""
    st.markdown(
        """
    <script>
        const main = window.parent.document.querySelector(
            'section.main'
        );
        if (main) {
            main.scrollTo(0, 0);
        }
    </script>
    """,
        unsafe_allow_html=True,
    )
    _apply_table_header_styles()
    st.title("Market Anomalies")
    _render_alert_table(alerts[alerts["alert_type"] == PRICE_ALERT], "Price Anomalies")
    _render_alert_table(alerts[alerts["alert_type"] == VOLUME_ALERT], "Volume Spikes")
    _render_alert_table(alerts[alerts["alert_type"] == PUMP_ALERT], "Pump-and-Dump Candidates")


def synthetic_cases_page(
    conn: sqlite3.Connection, alerts: pd.DataFrame, account_links: pd.DataFrame
) -> None:
    """Render synthetic surveillance case tables and status controls."""
    st.markdown(
        """
    <script>
        const main = window.parent.document.querySelector(
            'section.main'
        );
        if (main) {
            main.scrollTo(0, 0);
        }
    </script>
    """,
        unsafe_allow_html=True,
    )
    _apply_table_header_styles()
    st.title("Synthetic Surveillance Cases")
    synthetic = alerts[alerts["alert_type"].isin([WASH_ALERT, SPOOF_ALERT])]
    _render_alert_table(synthetic[synthetic["alert_type"] == WASH_ALERT], "Wash Trading Cases")
    _render_alert_table(synthetic[synthetic["alert_type"] == SPOOF_ALERT], "Spoofing/Layering Cases")

    st.subheader("Linked Accounts")
    _render_table(account_links)

    st.subheader("Case Status Update")
    _status_controls(conn, synthetic)


def alert_detail_page(
    conn: sqlite3.Connection, alerts: pd.DataFrame, candles: pd.DataFrame
) -> None:
    """Render one alert investigation detail view."""
    st.markdown(
        """
    <script>
        const main = window.parent.document.querySelector(
            'section.main'
        );
        if (main) {
            main.scrollTo(0, 0);
        }
    </script>
    """,
        unsafe_allow_html=True,
    )
    _apply_table_header_styles()
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
    severity = str(alert["severity"])
    severity_style = SEVERITY_COLORS.get(severity, {"bg": "rgba(0, 0, 0, 0.06)", "text": "#333"})
    cols[0].markdown(
        f"""
<div style="background-color: {severity_style["bg"]}; padding: 12px; border-radius: 8px; text-align: center;">
    <div style="font-size: 0.85rem; color: {severity_style["text"]};">Severity</div>
    <div style="font-size: 1.5rem; font-weight: bold; color: {severity_style["text"]};">{severity}</div>
</div>
""",
        unsafe_allow_html=True,
    )
    cols[1].metric("Severity Score", str(alert["severity_score"]))
    cols[2].metric("Status", str(alert["status"]))
    cols[3].metric("Symbol", str(alert.get("symbol") or "N/A"))
    cols[4].metric("Alert ID", str(alert_id))
    st.caption(f"Window: {alert['start_time']} to {alert['end_time']}")
    st.write(alert["evidence_summary"])
    st.subheader("Evidence")
    _render_table(evidence)

    st.subheader("Alert Window")
    window = _alert_window_candles(candles, alert)
    if window.empty:
        st.info("No market candles are available for this alert window.")
    else:
        st.line_chart(window.set_index("timestamp")[["close", "volume"]])

    st.subheader("Recommended Follow-Up")
    st.write(alert.get("recommended_follow_up") or "Review context and document disposition.")
    _status_controls(conn, alerts[alerts["alert_id"] == alert_id])

    st.subheader("Exports")
    selected_alert = alerts[alerts["alert_id"] == alert_id]
    st.download_button(
        "Download Case Report PDF",
        generate_case_report_pdf(alert, evidence),
        file_name=case_report_filename(alert),
        mime="application/pdf",
    )
    st.download_button(
        "Download Alert CSV",
        alerts_to_csv(selected_alert),
        file_name=alert_csv_filename(alert),
        mime="text/csv",
    )


def daily_report_page(
    alerts: pd.DataFrame, candles: pd.DataFrame, metadata: dict[str, str]
) -> None:
    """Render the daily surveillance report."""
    st.markdown(
        """
    <script>
        const main = window.parent.document.querySelector(
            'section.main'
        );
        if (main) {
            main.scrollTo(0, 0);
        }
    </script>
    """,
        unsafe_allow_html=True,
    )
    _apply_table_header_styles()
    st.title("Daily Report")
    summary = build_daily_report_summary(alerts, candles, metadata)
    data_source = str(summary["data_source"]).title()
    api_status = str(summary["api_status"]).title()
    if api_status == "Ok":
        api_status = "OK"

    header_columns = st.columns(3)
    header_columns[0].metric("Total Alerts", f"{summary['total_alerts']:,}")
    header_columns[1].metric("Symbols Monitored", f"{len(summary['symbols']):,}")
    header_columns[2].metric("Data Source", data_source)
    st.write(f"Report date: {summary['report_date']}")
    st.write(f"Symbols monitored: {', '.join(summary['symbols']) or 'None'}")
    st.caption(f"API status: {api_status} | Last fetched: {summary['last_fetched_at']}")

    st.subheader("Severity Summary")
    severity_counts = _severity_counts_dict(summary["severity_counts"])
    severity_columns = st.columns(4)
    severity_styles = {
        "Critical": SEVERITY_COLORS["Critical"],
        "High": SEVERITY_COLORS["High"],
        "Medium": SEVERITY_COLORS["Medium"],
        "Low": SEVERITY_COLORS["Low"],
    }
    for column, severity in zip(severity_columns, ["Critical", "High", "Medium", "Low"], strict=True):
        count = f"{severity_counts.get(severity, 0):,}"
        style = severity_styles[severity]
        column.markdown(
            f"""
<div style="background-color: {style["bg"]}; padding: 16px; border-radius: 8px; text-align: center;">
    <div style="font-size: 0.85rem; color: {style["text"]};">{severity}</div>
    <div style="font-size: 2rem; font-weight: bold; color: {style["text"]};">{count}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.subheader("Alert Type Breakdown")
    st.markdown(
        """
<style>
table td:nth-child(2), table th:nth-child(2) {
    text-align: center !important;
}
</style>
""",
        unsafe_allow_html=True,
    )
    alert_type_breakdown = _counts_frame(summary["type_counts"], "alert_type").rename(
        columns={"count": "Count"}
    )
    _render_table(alert_type_breakdown)

    st.subheader("Highest Severity Alerts")
    highest_alerts = alert_table(summary["highest_alerts"])
    _render_table(highest_alerts)

    st.subheader("Limitations")
    st.write(summary["limitations"])

    st.subheader("Exports")
    st.download_button(
        "Download Daily Report PDF",
        generate_daily_report_pdf(alerts, candles, metadata),
        file_name="daily_surveillance_report.pdf",
        mime="application/pdf",
    )
    st.download_button(
        "Download Alerts CSV",
        alerts_to_csv(alerts),
        file_name=daily_alerts_csv_filename(),
        mime="text/csv",
    )


def methodology_page() -> None:
    """Render methodology and limitations."""
    st.markdown(
        """
    <script>
        const main = window.parent.document.querySelector(
            'section.main'
        );
        if (main) {
            main.scrollTo(0, 0);
        }
    </script>
    """,
        unsafe_allow_html=True,
    )
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


def _render_alert_table(alerts: pd.DataFrame, label: str) -> None:
    """Render a standard alert table with a page-specific empty state."""
    st.subheader(label)
    _render_table(alert_table(alerts), empty_message=_empty_table_message(label))


def _render_table(
    frame: pd.DataFrame, empty_message: str = GENERIC_EMPTY_TABLE_MESSAGE
) -> None:
    if frame.empty:
        st.info(empty_message)
        return
    display = format_dataframe_for_display(frame).rename(columns=TABLE_DISPLAY_COLUMNS)
    dataframe = display.style.hide(axis="index")
    if "Severity" in display.columns:
        dataframe = dataframe.apply(color_severity_row, axis=1)
    dataframe = dataframe.set_table_styles(
        [
            {
                "selector": "th",
                "props": [
                    ("font-weight", "bold"),
                    ("text-align", "center"),
                ],
            }
        ]
    )
    st.markdown(dataframe.to_html(), unsafe_allow_html=True)


def _render_centered_overview_table(label: str, frame: pd.DataFrame) -> None:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown(
            f"""
<div style="display: flex; flex-direction: column; align-items: center;">
    <h3 style="white-space: nowrap; margin-bottom: 8px; text-align: center;">{label}</h3>
</div>
""",
            unsafe_allow_html=True,
        )
        display = format_dataframe_for_display(frame).rename(columns=TABLE_DISPLAY_COLUMNS)
        styled_df = display.style.hide(axis="index")
        table_styles = [
            {
                "selector": "table",
                "props": [("table-layout", "auto"), ("width", "auto")],
            },
            {
                "selector": "td:nth-child(1), th:nth-child(1)",
                "props": [("text-align", "left")],
            },
            {
                "selector": "td:nth-child(2), th:nth-child(2)",
                "props": [("text-align", "right")],
            },
        ]
        if label == "Top Abnormal-Volume Symbols":
            table_styles[0]["selector"] = ""
            table_styles[0]["props"] = [
                ("table-layout", "auto !important"),
                ("min-width", "280px !important"),
                ("word-wrap", "normal !important"),
                ("overflow-wrap", "normal !important"),
            ]
            table_styles.extend(
                [
                    {
                        "selector": "td",
                        "props": [
                            ("min-width", "90px !important"),
                            ("white-space", "nowrap !important"),
                            ("overflow", "visible !important"),
                            ("text-overflow", "clip !important"),
                            ("overflow-wrap", "normal !important"),
                            ("word-break", "normal !important"),
                        ],
                    },
                    {
                        "selector": "td:nth-child(2)",
                        "props": [("min-width", "120px !important")],
                    },
                    {
                        "selector": "th",
                        "props": [
                            ("white-space", "nowrap !important"),
                            ("overflow", "visible !important"),
                            ("text-overflow", "clip !important"),
                            ("overflow-wrap", "normal !important"),
                            ("word-break", "normal !important"),
                        ],
                    },
                    {
                        "selector": "th:nth-child(2)",
                        "props": [("min-width", "120px !important")],
                    },
                ]
            )
        styled_df = styled_df.set_table_styles(table_styles)
        st.markdown(
            "<div style='display:flex; justify-content:center;'>" + styled_df.to_html() + "</div>",
            unsafe_allow_html=True,
        )


def _format_top_volume_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    if "volume" in display.columns:
        volumes = pd.to_numeric(display["volume"], errors="coerce")
        display["volume"] = volumes.map(
            lambda value: "" if pd.isna(value) else f"{value:,.2f}"
        )
    return display


def _format_top_price_movement_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    if "absolute_return" in display.columns:
        returns = pd.to_numeric(display["absolute_return"], errors="coerce")
        display["absolute_return"] = returns.map(
            lambda value: "" if pd.isna(value) else f"{value:.4%}"
        )
    return display


def _apply_table_header_styles() -> None:
    st.markdown(TABLE_HEADER_STYLE, unsafe_allow_html=True)


def color_severity_row(row: pd.Series) -> list[str]:
    color = SEVERITY_COLORS.get(str(row["Severity"]), {}).get("bg", "")
    color = f"background-color: {color}" if color else ""
    return [color] * len(row)


def _empty_table_message(label: str) -> str:
    return EMPTY_TABLE_MESSAGES.get(label, GENERIC_EMPTY_TABLE_MESSAGE)


def _available_symbols(candles: pd.DataFrame) -> list[str]:
    if candles.empty or "symbol" not in candles:
        return []
    return sorted(candles["symbol"].dropna().astype(str).unique())


def _counts_frame(counts: pd.Series, label: str) -> pd.DataFrame:
    if counts.empty:
        return pd.DataFrame(columns=[label, "count"])
    return counts.rename_axis(label).reset_index(name="count")


def _severity_counts_dict(counts: pd.Series) -> dict[str, int]:
    if counts.empty:
        return {}
    return {str(label): int(count) for label, count in counts.items()}


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
