"""PDF case report generation."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


REPORT_TABLE_WIDTH = 500
EVIDENCE_COL_WIDTHS = [120, 80, 80, 220]


def generate_case_report_pdf(alert: pd.Series, evidence: pd.DataFrame) -> bytes:
    """Generate a structured PDF case report for one alert."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=56, rightMargin=56)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Case Report", styles["Title"]),
        Spacer(1, 12),
        _details_table(alert, styles),
        Spacer(1, 14),
        Paragraph("Trigger Summary", styles["Heading2"]),
        _paragraph(_value(alert, "evidence_summary", "No summary available."), styles["BodyText"]),
        Spacer(1, 10),
        Paragraph("Evidence", styles["Heading2"]),
        _evidence_table(evidence, styles),
        Spacer(1, 10),
        Paragraph("Recommended Follow-Up", styles["Heading2"]),
        _paragraph(
            _value(
                alert,
                "recommended_follow_up",
                "Review context and document disposition.",
            ),
            styles["BodyText"],
        ),
        Spacer(1, 10),
        Paragraph("Limitations", styles["Heading2"]),
        Paragraph(
            "This alert is a surveillance lead. It is not an accusation and should "
            "be assessed with market context, available account records, and "
            "applicable policy.",
            styles["BodyText"],
        ),
        Spacer(1, 10),
        Paragraph("Generated At", styles["Heading2"]),
        Paragraph(_format_timestamp(datetime.now(UTC)), styles["BodyText"]),
    ]
    doc.build(story)
    return buffer.getvalue()


def case_report_filename(alert: pd.Series, generated_at: datetime | None = None) -> str:
    """Return the download filename for a case report PDF."""
    alert_id = _plain_text(_value(alert, "alert_id", "Unassigned"))
    report_date = (generated_at or datetime.now(UTC)).astimezone(UTC).date().isoformat()
    return f"Surveillance_Case_Report_{alert_id}_{report_date}.pdf"


def _details_table(alert: pd.Series, styles: dict[str, object]) -> Table:
    alert_id = _value(alert, "alert_id", "Unassigned")
    header_style = _table_header_style(styles)
    cell_style = _table_cell_style(styles)
    rows = [
        [_paragraph("Alert ID", header_style), _paragraph(alert_id, cell_style)],
        [_paragraph("Alert Type", header_style), _paragraph(_value(alert, "alert_type", "Alert"), cell_style)],
        [_paragraph("Severity", header_style), _paragraph(_value(alert, "severity", ""), cell_style)],
        [_paragraph("Severity Score", header_style), _paragraph(_value(alert, "severity_score", ""), cell_style)],
        [_paragraph("Status", header_style), _paragraph(_value(alert, "status", "New"), cell_style)],
        [_paragraph("Symbol", header_style), _paragraph(_value(alert, "symbol", "N/A"), cell_style)],
        [
            _paragraph("Time Window", header_style),
            _paragraph(
                f"{_format_timestamp(_value(alert, 'start_time', ''))} to "
                f"{_format_timestamp(_value(alert, 'end_time', ''))}",
                cell_style,
            ),
        ],
    ]
    account_id = _value(alert, "account_id", None)
    if account_id is not None:
        rows.append([_paragraph("Account ID", header_style), _paragraph(account_id, cell_style)])
    table = Table(rows, colWidths=[120, REPORT_TABLE_WIDTH - 120], rowHeights=[None] * len(rows))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _evidence_table(evidence: pd.DataFrame, styles: dict[str, object]) -> Table | Paragraph:
    if evidence.empty:
        return Paragraph("No evidence rows available.", styles["BodyText"])
    header_style = _table_header_style(styles)
    cell_style = _table_cell_style(styles)
    rows = [
        [
            _paragraph("Metric", header_style),
            _paragraph("Value", header_style),
            _paragraph("Threshold", header_style),
            _paragraph("Explanation", header_style),
        ]
    ]
    for row in evidence.to_dict("records"):
        threshold = row.get("threshold_value")
        operator = row.get("comparison_operator") or ""
        threshold_text = ""
        if pd.notna(threshold):
            threshold_text = f"{operator} {threshold}".strip()
        rows.append(
            [
                _paragraph(row.get("metric_name", ""), cell_style),
                _paragraph(row.get("metric_value", ""), cell_style),
                _paragraph(threshold_text, cell_style),
                _paragraph(row.get("explanation", ""), cell_style),
            ]
        )
    table = Table(rows, colWidths=EVIDENCE_COL_WIDTHS, rowHeights=[None] * len(rows))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _value(alert: pd.Series, key: str, default: object) -> object:
    value = alert.get(key, default)
    if pd.isna(value):
        return default
    return value


def _paragraph(value: object, style: object) -> Paragraph:
    return Paragraph(escape(_plain_text(value)), style)


def _table_header_style(styles: dict[str, object]) -> ParagraphStyle:
    return ParagraphStyle(
        "CaseReportTableHeader",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        wordWrap="CJK",
    )


def _table_cell_style(styles: dict[str, object]) -> ParagraphStyle:
    return ParagraphStyle(
        "CaseReportTableCell",
        parent=styles["BodyText"],
        fontSize=9,
        leading=11,
        wordWrap="CJK",
    )


def _plain_text(value: object) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&amp;", "&")
    )


def _format_timestamp(value: object) -> str:
    if value is None:
        return ""
    timestamp = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(timestamp):
        return _plain_text(value)
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")
