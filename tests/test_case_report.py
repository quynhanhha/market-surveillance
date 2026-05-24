"""Report artifact tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from src.reporting.case_report import generate_case_report_pdf
from src.reporting.daily_summary import (
    ALERT_CSV_COLUMNS,
    alert_csv_filename,
    alerts_to_csv,
    daily_alerts_csv_filename,
    generate_daily_report_pdf,
)


def test_case_report_pdf_returns_pdf_bytes() -> None:
    pdf = generate_case_report_pdf(_alert(), _evidence())

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 100


def test_case_report_pdf_generation_succeeds_with_severity_score() -> None:
    alert = _alert()
    alert["severity_score"] = 82

    pdf = generate_case_report_pdf(alert, _evidence())

    assert pdf.startswith(b"%PDF")


def test_case_report_pdf_generation_succeeds_with_empty_evidence() -> None:
    pdf = generate_case_report_pdf(_alert(), pd.DataFrame())

    assert pdf.startswith(b"%PDF")


def test_daily_report_pdf_returns_pdf_bytes() -> None:
    pdf = generate_daily_report_pdf(_alerts(), _candles(), {"data_source": "sample"})

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 100


def test_alert_csv_includes_severity_score() -> None:
    csv = alerts_to_csv(_alerts()).decode("utf-8")

    assert "severity_score" in csv.splitlines()[0]
    assert "82" in csv


def test_alert_csv_formats_timestamps_and_decodes_entities() -> None:
    alerts = _alerts()
    alerts.loc[0, "evidence_summary"] = "Threshold &gt;= expected &amp; valid"

    csv = alerts_to_csv(alerts).decode("utf-8")

    assert "2026-05-23 10:00 UTC" in csv
    assert "Threshold >= expected & valid" in csv
    assert "&gt;=" not in csv


def test_csv_filenames_include_report_date() -> None:
    generated_at = datetime(2026, 5, 24, tzinfo=UTC)

    assert alert_csv_filename(_alert(), generated_at) == "Surveillance_Case_Report_1_2026-05-24.csv"
    assert daily_alerts_csv_filename(generated_at) == "Surveillance_Alerts_2026-05-24.csv"


def test_empty_alert_csv_includes_expected_headers() -> None:
    csv = alerts_to_csv(pd.DataFrame()).decode("utf-8")

    assert csv.splitlines()[0] == ",".join(ALERT_CSV_COLUMNS)


def _alert() -> pd.Series:
    return _alerts().iloc[0]


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
            }
        ]
    )


def _evidence() -> pd.DataFrame:
    return pd.DataFrame(
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
