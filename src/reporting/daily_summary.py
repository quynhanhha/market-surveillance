"""Daily surveillance report artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from html import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ALERT_CSV_COLUMNS = [
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


def generate_daily_report_pdf(
    alerts: pd.DataFrame, candles: pd.DataFrame, metadata: dict[str, str]
) -> bytes:
    """Generate a formatted daily surveillance PDF report."""
    summary = build_daily_report_summary(alerts, candles, metadata)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Daily Surveillance Report", styles["Title"]),
        Spacer(1, 12),
        _key_value_table(
            [
                ("Report Date", summary["report_date"]),
                ("Data Source", summary["data_source"]),
                ("API Status", summary["api_status"]),
                ("Last Fetched", summary["last_fetched_at"]),
                ("Symbols Monitored", ", ".join(summary["symbols"]) or "None"),
                ("Total Alerts", str(summary["total_alerts"])),
                ("Generated At", summary["generated_at"]),
            ]
        ),
        Spacer(1, 14),
        Paragraph("Severity Summary", styles["Heading2"]),
        _counts_table(summary["severity_counts"], "Severity"),
        Spacer(1, 10),
        Paragraph("Alert Type Summary", styles["Heading2"]),
        _counts_table(summary["type_counts"], "Alert Type"),
        Spacer(1, 10),
        Paragraph("Highest Severity Alerts", styles["Heading2"]),
        _alerts_table(summary["highest_alerts"]),
        Spacer(1, 10),
        Paragraph("Limitations", styles["Heading2"]),
        Paragraph(summary["limitations"], styles["BodyText"]),
    ]
    doc.build(story)
    return buffer.getvalue()


def alerts_to_csv(alerts: pd.DataFrame) -> bytes:
    """Serialize alert table rows to CSV bytes with stable headers."""
    frame = alerts.copy()
    for column in ALERT_CSV_COLUMNS:
        if column not in frame:
            frame[column] = pd.NA
    extra_columns = [column for column in frame.columns if column not in ALERT_CSV_COLUMNS]
    output = frame[[*ALERT_CSV_COLUMNS, *extra_columns]].copy()
    for column in output.columns:
        output[column] = output[column].map(lambda value: _csv_value(value, column))
    return output.to_csv(index=False).encode("utf-8")


def alert_csv_filename(alert: pd.Series, generated_at: datetime | None = None) -> str:
    """Return the download filename for a single-alert CSV export."""
    alert_id = _plain_text(alert.get("alert_id", "Unassigned"))
    report_date = (generated_at or datetime.now(UTC)).astimezone(UTC).date().isoformat()
    return f"Surveillance_Case_Report_{alert_id}_{report_date}.csv"


def daily_alerts_csv_filename(generated_at: datetime | None = None) -> str:
    """Return the download filename for the daily alerts CSV export."""
    report_date = (generated_at or datetime.now(UTC)).astimezone(UTC).date().isoformat()
    return f"Surveillance_Alerts_{report_date}.csv"


def build_daily_report_summary(
    alerts: pd.DataFrame, candles: pd.DataFrame, metadata: dict[str, str]
) -> dict[str, object]:
    """Return daily report sections for UI rendering and PDF generation."""
    data_source = metadata.get("data_source", "unknown")
    symbols = (
        sorted(str(symbol) for symbol in candles["symbol"].dropna().unique())
        if "symbol" in candles
        else []
    )
    severity_counts = _counts(alerts, "severity")
    type_counts = _counts(alerts, "alert_type")
    highest = alerts.sort_values("severity_score", ascending=False).head(5) if not alerts.empty else alerts
    generated_at = datetime.now(UTC)
    return {
        "report_date": generated_at.date().isoformat(),
        "data_source": data_source,
        "api_status": metadata.get("api_status", "unknown"),
        "last_fetched_at": metadata.get("last_fetched_at", ""),
        "symbols": symbols,
        "total_alerts": len(alerts),
        "severity_counts": severity_counts,
        "type_counts": type_counts,
        "highest_alerts": highest,
        "limitations": (
            "Public market APIs do not expose private account identifiers or full "
            "order lifecycle records. Account-level scenarios in this prototype are "
            "deterministic synthetic data, not real accounts or transactions. SQLite "
            "storage is ephemeral in the deployed demo."
        ),
        "generated_at": generated_at.isoformat(),
    }


def _counts(frame: pd.DataFrame, column: str) -> pd.Series:
    if frame.empty or column not in frame:
        return pd.Series(dtype="int64")
    return frame[column].fillna("Unknown").value_counts()


def _key_value_table(rows: list[tuple[str, str]]) -> Table:
    table = Table([[_text(label), _text(value)] for label, value in rows], colWidths=[130, 350])
    table.setStyle(_table_style(header=False))
    return table


def _counts_table(counts: pd.Series, label: str) -> Table:
    rows = [[label, "Count"]]
    rows.extend([[_text(index), str(count)] for index, count in counts.items()])
    if len(rows) == 1:
        rows.append(["No rows.", "0"])
    table = Table(rows, colWidths=[260, 80])
    table.setStyle(_table_style())
    return table


def _alerts_table(alerts: pd.DataFrame) -> Table:
    rows = [["Alert ID", "Type", "Symbol", "Severity", "Score", "Status"]]
    for row in alerts.itertuples():
        rows.append(
            [
                _text(getattr(row, "alert_id", "")),
                _text(getattr(row, "alert_type", "")),
                _text(getattr(row, "symbol", "") or "N/A"),
                _text(getattr(row, "severity", "")),
                _text(getattr(row, "severity_score", "")),
                _text(getattr(row, "status", "")),
            ]
        )
    if len(rows) == 1:
        rows.append(["No alerts.", "", "", "", "", ""])
    table = Table(rows, colWidths=[55, 145, 85, 70, 45, 80])
    table.setStyle(_table_style())
    return table


def _table_style(header: bool = True) -> TableStyle:
    commands = [
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    else:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ]
        )
    return TableStyle(commands)


def _text(value: object) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return escape(str(value))


def _csv_value(value: object, column: str) -> str:
    if value is None or pd.isna(value):
        return ""
    if _is_timestamp_column(column):
        return _format_timestamp(value)
    return _plain_text(value)


def _is_timestamp_column(column: str) -> bool:
    return column.endswith("_time") or column.endswith("_at") or column == "timestamp"


def _format_timestamp(value: object) -> str:
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        return _plain_text(value)
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")


def _plain_text(value: object) -> str:
    return (
        str(value)
        .replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&amp;", "&")
    )
