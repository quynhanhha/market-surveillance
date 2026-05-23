"""Dashboard repository helper tests."""

from __future__ import annotations

from src.detection.severity import make_dedup_key
from src.storage.db import connect_sqlite
from src.storage.repositories import (
    fetch_alert_evidence,
    fetch_alerts,
    insert_alerts,
    update_alert_status,
)
from src.storage.schema import create_schema
from tests.test_alert_dedup import alert_frame


def test_fetch_alerts_includes_severity_score_and_account_id() -> None:
    conn = connect_sqlite()
    create_schema(conn)
    alerts = alert_frame("BTC/USDT")
    alerts.loc[0, "account_id"] = "ACC_0001"
    alerts.loc[0, "dedup_key"] = make_dedup_key(
        "Volume Spike",
        "BTC/USDT",
        "2026-05-23T10:00:00+00:00",
        "2026-05-23T10:00:00+00:00",
        "ACC_0001",
    )
    insert_alerts(conn, alerts)

    fetched = fetch_alerts(conn)

    assert "severity_score" in fetched.columns
    assert "account_id" in fetched.columns
    assert fetched.loc[0, "account_id"] == "ACC_0001"


def test_update_alert_status_persists() -> None:
    conn = connect_sqlite()
    create_schema(conn)
    insert_alerts(conn, alert_frame("BTC/USDT"))
    alert_id = int(fetch_alerts(conn).loc[0, "alert_id"])

    update_alert_status(conn, alert_id, "Escalated")

    assert fetch_alerts(conn).loc[0, "status"] == "Escalated"


def test_fetch_alert_evidence_returns_expected_rows() -> None:
    conn = connect_sqlite()
    create_schema(conn)
    insert_alerts(conn, alert_frame("BTC/USDT"))
    alert_id = int(fetch_alerts(conn).loc[0, "alert_id"])

    evidence = fetch_alert_evidence(conn, alert_id)

    assert evidence["metric_name"].tolist() == ["volume_z_score"]
