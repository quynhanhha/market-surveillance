"""Markdown case report generation."""

from __future__ import annotations

import pandas as pd


def generate_case_report(alert: pd.Series, evidence: pd.DataFrame) -> str:
    """Generate a concise analyst case note for one alert."""
    alert_id = _value(alert, "alert_id", "Unassigned")
    title = _value(alert, "alert_type", "Alert")
    lines = [
        f"# Case Note: {title}",
        "",
        f"- Alert ID: {alert_id}",
        f"- Status: {_value(alert, 'status', 'New')}",
        f"- Severity: {_value(alert, 'severity', '')} ({_value(alert, 'severity_score', '')})",
        f"- Symbol: {_value(alert, 'symbol', 'N/A')}",
        f"- Account: {_value(alert, 'account_id', 'N/A')}",
        f"- Window: {_value(alert, 'start_time', '')} to {_value(alert, 'end_time', '')}",
        "",
        "## Alert Summary",
        str(_value(alert, "evidence_summary", "No summary available.")),
        "",
        "## Evidence",
    ]
    if evidence.empty:
        lines.append("No evidence rows were stored for this alert.")
    else:
        for row in evidence.to_dict("records"):
            threshold = row.get("threshold_value")
            operator = row.get("comparison_operator") or ""
            threshold_text = (
                f" threshold {operator} {threshold}" if pd.notna(threshold) else ""
            )
            lines.append(
                f"- {row['metric_name']}: {row.get('metric_value')}{threshold_text}. "
                f"{row.get('explanation', '')}"
            )
    lines.extend(
        [
            "",
            "## Recommended Follow-Up",
            str(_value(alert, "recommended_follow_up", "Review context and document disposition.")),
            "",
            "## Analyst Note",
            "This alert is a surveillance lead. It is not an accusation and should be assessed with market context, available account records, and applicable policy.",
        ]
    )
    return "\n".join(lines)


def _value(alert: pd.Series, key: str, default: object) -> object:
    value = alert.get(key, default)
    if pd.isna(value):
        return default
    return value
