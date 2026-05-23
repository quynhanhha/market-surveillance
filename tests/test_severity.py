"""Unified severity scoring tests."""

from __future__ import annotations

import re

from src.detection.severity import (
    make_dedup_key,
    primary_metric_z_score_points,
    severity_from_score,
    spoof_repeated_events_points,
    wash_trade_count_points,
)


def test_severity_boundaries_are_global() -> None:
    """Score labels use one shared Low/Medium/High mapping."""
    assert severity_from_score(44) == "Low"
    assert severity_from_score(45) == "Medium"
    assert severity_from_score(74) == "Medium"
    assert severity_from_score(75) == "High"


def test_z_score_component_bands_are_shared() -> None:
    """Primary metric z-score points match Section 10.1 bands."""
    assert primary_metric_z_score_points(2.99) == 0
    assert primary_metric_z_score_points(3.0) == 15
    assert primary_metric_z_score_points(4.0) == 25
    assert primary_metric_z_score_points(6.01) == 40


def test_rule_specific_band_helpers_live_in_severity() -> None:
    """Rule band helpers are centralized in severity.py."""
    assert wash_trade_count_points(5) == 15
    assert wash_trade_count_points(10) == 25
    assert spoof_repeated_events_points(3) == 15
    assert spoof_repeated_events_points(6) == 25


def test_dedup_key_is_deterministic_and_sensitive_to_subject() -> None:
    """Dedup keys are deterministic SHA-256 prefixes."""
    first = make_dedup_key(
        "Volume Spike",
        "BTC/USDT",
        "2026-05-23T10:00:00+00:00",
        "2026-05-23T10:00:00+00:00",
    )
    second = make_dedup_key(
        "Volume Spike",
        "BTC/USDT",
        "2026-05-23T10:00:00+00:00",
        "2026-05-23T10:00:00+00:00",
    )
    different = make_dedup_key(
        "Volume Spike",
        "ETH/USDT",
        "2026-05-23T10:00:00+00:00",
        "2026-05-23T10:00:00+00:00",
    )

    assert first == second
    assert first != different
    assert re.fullmatch(r"[0-9a-f]{32}", first)
