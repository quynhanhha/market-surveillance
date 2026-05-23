"""Dashboard helper tests."""

from __future__ import annotations

import pandas as pd

from src.reporting.case_report import generate_case_report
from src.reporting.daily_summary import generate_daily_summary
from src.ui.components import alert_table, filter_alerts
from src.ui.pages import build_overview_summary, market_anomaly_tables


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


def test_daily_report_includes_source_severity_summary_and_limitations() -> None:
    report = generate_daily_summary(
        _alerts(),
        _candles(),
        {"data_source": "sample", "api_status": "unavailable"},
    )

    assert "Data source: sample" in report
    assert "## Severity Summary" in report
    assert "## Limitations" in report


def test_case_report_includes_alert_evidence_score_and_follow_up() -> None:
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

    report = generate_case_report(alert, evidence)

    assert "Alert ID: 1" in report
    assert "Severity: High (82)" in report
    assert "return_z_score" in report
    assert "Recommended Follow-Up" in report


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
