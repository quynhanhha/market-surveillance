"""Unified alert severity scoring and deduplication helpers."""

from __future__ import annotations

import hashlib


HIGH_SEVERITY_SCORE = 75
MEDIUM_SEVERITY_SCORE = 45

ZSCORE_3_TO_4_POINTS = 15
ZSCORE_4_TO_6_POINTS = 25
ZSCORE_OVER_6_POINTS = 40
REPEATED_EVENTS_POINTS = 20
LINKED_ACCOUNTS_POINTS = 20
HIGH_NOTIONAL_POINTS = 15
MULTIPLE_RULES_POINTS = 25
RAPID_REVERSAL_POINTS = 15
HIGH_LINK_CONFIDENCE_POINTS = 10
CORROBORATION_POINTS = 15
PUMP_STRONG_RETURN_POINTS = 25
PUMP_ALL_CONDITIONS_POINTS = 10
SPOOF_REPEATED_3_TO_5_POINTS = 15
SPOOF_REPEATED_OVER_5_POINTS = 25


def severity_from_score(score: int) -> str:
    """Map a 0-100 score to the shared severity label."""
    if score >= HIGH_SEVERITY_SCORE:
        return "High"
    if score >= MEDIUM_SEVERITY_SCORE:
        return "Medium"
    return "Low"


def make_dedup_key(
    alert_type: str,
    symbol: str | None,
    start_time: str,
    end_time: str,
    account_id: str | None = None,
) -> str:
    """Build the deterministic Section 10.3 alert deduplication key."""
    raw = f"{alert_type}|{symbol or ''}|{start_time}|{end_time}|{account_id or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def primary_metric_z_score_points(z_score: float) -> int:
    """Return the shared z-score band contribution."""
    absolute_z_score = abs(z_score)
    if absolute_z_score > 6:
        return ZSCORE_OVER_6_POINTS
    if absolute_z_score >= 4:
        return ZSCORE_4_TO_6_POINTS
    if absolute_z_score >= 3:
        return ZSCORE_3_TO_4_POINTS
    return 0


def repeated_events_points(count: int) -> int:
    """Return the shared repeated-events contribution."""
    if count >= 3:
        return REPEATED_EVENTS_POINTS
    return 0


def linked_accounts_points(confirmed: bool) -> int:
    """Return the shared linked-account contribution."""
    return LINKED_ACCOUNTS_POINTS if confirmed else 0


def high_notional_points(confirmed: bool) -> int:
    """Return the shared high-notional contribution."""
    return HIGH_NOTIONAL_POINTS if confirmed else 0


def multiple_rules_points(confirmed: bool) -> int:
    """Return the shared cross-rule contribution."""
    return MULTIPLE_RULES_POINTS if confirmed else 0


def rapid_reversal_points(confirmed: bool) -> int:
    """Return the shared rapid-reversal contribution."""
    return RAPID_REVERSAL_POINTS if confirmed else 0


def high_link_confidence_points(confidence: float) -> int:
    """Return the shared high-link-confidence contribution."""
    return HIGH_LINK_CONFIDENCE_POINTS if confidence > 0.85 else 0


def volume_multiplier_points(confirmed: bool) -> int:
    """Return the volume-spike corroboration contribution."""
    return CORROBORATION_POINTS if confirmed else 0


def pump_return_points(pump_return: float) -> int:
    """Return pump-return contribution for pump-and-dump scoring."""
    if pump_return > 0.08:
        return PUMP_STRONG_RETURN_POINTS
    if pump_return >= 0.05:
        return ZSCORE_3_TO_4_POINTS
    return 0


def pump_all_conditions_points(confirmed: bool) -> int:
    """Return all-conditions corroboration for pump-and-dump scoring."""
    return PUMP_ALL_CONDITIONS_POINTS if confirmed else 0


def wash_trade_count_points(trade_count: int) -> int:
    """Return wash-trading trade-count contribution."""
    if trade_count >= 10:
        return ZSCORE_4_TO_6_POINTS
    if trade_count >= 5:
        return ZSCORE_3_TO_4_POINTS
    return 0


def spoof_repeated_events_points(count: int) -> int:
    """Return spoofing/layering repeated-event contribution."""
    if count > 5:
        return SPOOF_REPEATED_OVER_5_POINTS
    if count >= 3:
        return SPOOF_REPEATED_3_TO_5_POINTS
    return 0


def volume_spike_score(z_score: float, volume_multiplier_confirmed: bool) -> int:
    """Score a volume spike alert."""
    return (
        primary_metric_z_score_points(z_score)
        + volume_multiplier_points(volume_multiplier_confirmed)
    )


def price_anomaly_score(z_score: float) -> int:
    """Score a price anomaly alert."""
    return primary_metric_z_score_points(z_score)


def pump_dump_score(
    pump_return: float,
    volume_confirmed: bool,
    reversal_confirmed: bool,
    all_conditions_confirmed: bool,
    multiple_rules_confirmed: bool,
) -> int:
    """Score a pump-and-dump candidate alert."""
    return (
        pump_return_points(pump_return)
        + volume_multiplier_points(volume_confirmed)
        + rapid_reversal_points(reversal_confirmed)
        + pump_all_conditions_points(all_conditions_confirmed)
        + multiple_rules_points(multiple_rules_confirmed)
    )


def wash_trading_score(
    trade_count: int,
    linked_accounts_confirmed: bool,
    link_confidence: float,
    high_notional_confirmed: bool,
) -> int:
    """Score a synthetic wash-trading alert."""
    return (
        wash_trade_count_points(trade_count)
        + linked_accounts_points(linked_accounts_confirmed)
        + high_link_confidence_points(link_confidence)
        + high_notional_points(high_notional_confirmed)
    )


def spoofing_layering_score(
    repeated_count: int,
    linked_coordination_confirmed: bool,
    high_notional_confirmed: bool,
) -> int:
    """Score a synthetic spoofing/layering alert."""
    return (
        spoof_repeated_events_points(repeated_count)
        + linked_accounts_points(linked_coordination_confirmed)
        + high_notional_points(high_notional_confirmed)
    )
