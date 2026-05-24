"""Dashboard helper tests."""

from __future__ import annotations

import pandas as pd

from src.reporting.case_report import generate_case_report_pdf
from src.reporting.daily_summary import (
    alerts_to_csv,
    build_daily_report_summary,
    generate_daily_report_pdf,
)
from src.ui.components import alert_table, filter_alerts
from src.ui.pages import build_overview_summary, market_anomaly_tables
from src.ui import pages


def test_filter_alerts_applies_severity_status_symbol_and_date_range() -> None:
    alerts = _alerts()
    filtered = filter_alerts(
        alerts,
        {
            "symbol": "BTC/USDT",
            "severity": ["High"],
            "status": ["New"],
            "start_time": "2026-05-23T09:30:00+00:00",
            "end_time": "2026-05-23T10:30:00+00:00",
        },
    )

    assert filtered["alert_id"].tolist() == [1]


def test_alert_table_includes_severity_score() -> None:
    table = alert_table(_alerts())

    assert "severity_score" in table.columns


def test_overview_summary_includes_totals_by_severity_and_type() -> None:
    summary = build_overview_summary(_alerts())

    assert summary["total_alerts"] == 2
    assert set(summary["by_severity"]["severity"]) == {"High", "Low"}
    assert set(summary["by_type"]["alert_type"]) == {"Price Anomaly", "Volume Spike"}


def test_market_anomaly_tables_include_severity_score() -> None:
    tables = market_anomaly_tables(_alerts())

    assert "severity_score" in tables["price"].columns
    assert "severity_score" in tables["volume"].columns


def test_render_table_outputs_styled_html(monkeypatch) -> None:
    rendered: dict[str, object] = {}

    def fake_markdown(body: str, unsafe_allow_html: bool = False) -> None:
        rendered["body"] = body
        rendered["unsafe_allow_html"] = unsafe_allow_html

    monkeypatch.setattr(pages.st, "markdown", fake_markdown)

    pages._render_table(alert_table(_alerts().head(1)))

    body = str(rendered["body"])
    assert rendered["unsafe_allow_html"] is True
    assert "<table" in body
    assert "font-weight: bold" in body
    assert "text-align: center" in body
    assert "background-color: rgba(255, 107, 107, 0.2)" in body
    assert "blank level0" not in body


def test_render_table_empty_state_uses_info(monkeypatch) -> None:
    rendered: dict[str, str] = {}

    def fake_info(message: str) -> None:
        rendered["message"] = message

    def fake_markdown(body: str, unsafe_allow_html: bool = False) -> None:
        rendered["body"] = body

    monkeypatch.setattr(pages.st, "info", fake_info)
    monkeypatch.setattr(pages.st, "markdown", fake_markdown)

    pages._render_table(pd.DataFrame(), empty_message="Nothing here.")

    assert rendered == {"message": "Nothing here."}


def test_daily_report_helpers_are_callable() -> None:
    summary = build_daily_report_summary(
        _alerts(),
        _candles(),
        {"data_source": "sample", "api_status": "unavailable"},
    )
    pdf = generate_daily_report_pdf(
        _alerts(),
        _candles(),
        {"data_source": "sample", "api_status": "unavailable"},
    )
    csv = alerts_to_csv(_alerts())

    assert summary["data_source"] == "sample"
    assert "severity_counts" in summary
    assert "limitations" in summary
    assert pdf.startswith(b"%PDF")
    assert b"severity_score" in csv


def test_case_report_helper_is_callable_with_evidence_score_and_follow_up() -> None:
    alert = _alerts().iloc[0]
    evidence = pd.DataFrame(
        [
            {
                "metric_name": "return_z_score",
                "metric_value": 4.2,
                "threshold_value": 3.0,
                "comparison_operator": ">",
                "explanation": "Return z-score over rolling window.",
            }
        ]
    )

    report = generate_case_report_pdf(alert, evidence)

    assert report.startswith(b"%PDF")


def _alerts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "alert_id": 1,
                "alert_type": "Price Anomaly",
                "severity": "High",
                "severity_score": 82,
                "status": "New",
                "exchange": "coinbase",
                "symbol": "BTC/USDT",
                "account_id": None,
                "start_time": "2026-05-23T10:00:00+00:00",
                "end_time": "2026-05-23T10:00:00+00:00",
                "evidence_summary": "BTC abnormal return.",
                "recommended_follow_up": "Review market context.",
            },
            {
                "alert_id": 2,
                "alert_type": "Volume Spike",
                "severity": "Low",
                "severity_score": 30,
                "status": "Closed",
                "exchange": "coinbase",
                "symbol": "ETH/USDT",
                "account_id": None,
                "start_time": "2026-05-23T12:00:00+00:00",
                "end_time": "2026-05-23T12:00:00+00:00",
                "evidence_summary": "ETH volume spike.",
                "recommended_follow_up": "Review liquidity.",
            },
        ]
    )


def _candles() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "BTC/USDT",
                "timestamp": "2026-05-23T10:00:00+00:00",
                "open": 100.0,
                "close": 106.0,
            }
        ]
    )
