"""Synthetic wash-trading detection."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd

from src.config.thresholds import (
    LINK_CONFIDENCE_THRESHOLD,
    MAX_NET_POSITION_RATIO,
    MIN_NOTIONAL,
    MIN_PAIR_TRADES,
    TIME_WINDOW_HOURS,
)
from src.detection.severity import (
    make_dedup_key,
    severity_from_score,
    wash_trading_score,
)


ALERT_TYPE = "Synthetic Wash Trading Pattern"
RECOMMENDED_FOLLOW_UP = "Review beneficial ownership, funding source, and pair trading history."


def detect_wash_trading(
    synthetic_trades: pd.DataFrame, account_links: pd.DataFrame
) -> pd.DataFrame:
    """Detect linked account pairs trading back and forth with low net position change."""
    required_trade_columns = {
        "timestamp",
        "symbol",
        "buyer_account_id",
        "seller_account_id",
        "quantity",
        "notional_value",
    }
    missing_trade_columns = required_trade_columns.difference(synthetic_trades.columns)
    if missing_trade_columns:
        raise ValueError(f"Synthetic trades missing columns: {sorted(missing_trade_columns)}")
    required_link_columns = {"account_id_a", "account_id_b", "link_type", "confidence"}
    missing_link_columns = required_link_columns.difference(account_links.columns)
    if missing_link_columns:
        raise ValueError(f"Account links missing columns: {sorted(missing_link_columns)}")
    if synthetic_trades.empty or account_links.empty:
        return _empty_alerts()

    trades = synthetic_trades.copy()
    trades["timestamp"] = pd.to_datetime(trades["timestamp"], utc=True)
    trades["notional_value"] = pd.to_numeric(trades["notional_value"], errors="coerce")
    trades["quantity"] = pd.to_numeric(trades["quantity"], errors="coerce")
    trades["account_a"] = trades[["buyer_account_id", "seller_account_id"]].min(axis=1)
    trades["account_b"] = trades[["buyer_account_id", "seller_account_id"]].max(axis=1)
    links = account_links.copy()
    links["account_a"] = links[["account_id_a", "account_id_b"]].min(axis=1)
    links["account_b"] = links[["account_id_a", "account_id_b"]].max(axis=1)

    alerts: list[dict[str, Any]] = []
    for (account_a, account_b, symbol), group in trades.groupby(
        ["account_a", "account_b", "symbol"], sort=False
    ):
        link = links[(links["account_a"] == account_a) & (links["account_b"] == account_b)]
        if link.empty:
            continue
        link_row = link.iloc[0]
        link_confidence = float(link_row["confidence"])
        if link_confidence < LINK_CONFIDENCE_THRESHOLD:
            continue
        candidate = _best_pair_window(group.sort_values("timestamp"), str(account_a))
        if candidate is None:
            continue
        start_time, end_time, trade_count, notional_value, net_position_ratio = candidate
        if (
            trade_count >= MIN_PAIR_TRADES
            and notional_value >= MIN_NOTIONAL
            and net_position_ratio <= MAX_NET_POSITION_RATIO
        ):
            alerts.append(
                _alert_from_window(
                    str(account_a),
                    str(account_b),
                    str(symbol),
                    str(link_row["link_type"]),
                    link_confidence,
                    start_time,
                    end_time,
                    trade_count,
                    notional_value,
                    net_position_ratio,
                )
            )
    return pd.DataFrame(alerts)


def _best_pair_window(
    trades: pd.DataFrame, account_a: str
) -> tuple[str, str, int, float, float] | None:
    best: tuple[str, str, int, float, float] | None = None
    window_size = timedelta(hours=TIME_WINDOW_HOURS)
    for _, start_row in trades.iterrows():
        start_timestamp = start_row["timestamp"]
        end_timestamp = start_timestamp + window_size
        window = trades[
            (trades["timestamp"] >= start_timestamp)
            & (trades["timestamp"] <= end_timestamp)
        ]
        if window.empty:
            continue
        bought = window.loc[window["buyer_account_id"] == account_a, "quantity"].sum()
        sold = window.loc[window["seller_account_id"] == account_a, "quantity"].sum()
        total_quantity = window["quantity"].sum()
        if total_quantity == 0:
            continue
        net_position_ratio = abs(float(bought - sold)) / float(total_quantity)
        trade_count = int(len(window))
        notional_value = float(window["notional_value"].sum())
        candidate = (
            start_timestamp.isoformat(),
            window["timestamp"].max().isoformat(),
            trade_count,
            notional_value,
            net_position_ratio,
        )
        if best is None or (candidate[2], candidate[3]) > (best[2], best[3]):
            best = candidate
    return best


def _alert_from_window(
    account_a: str,
    account_b: str,
    symbol: str,
    link_type: str,
    link_confidence: float,
    start_time: str,
    end_time: str,
    trade_count: int,
    notional_value: float,
    net_position_ratio: float,
) -> dict[str, Any]:
    account_pair = f"{account_a}|{account_b}"
    score = wash_trading_score(
        trade_count=trade_count,
        linked_accounts_confirmed=True,
        link_confidence=link_confidence,
        high_notional_confirmed=notional_value >= MIN_NOTIONAL,
    )
    severity = severity_from_score(score)
    return {
        "alert_type": ALERT_TYPE,
        "severity": severity,
        "severity_score": score,
        "exchange": None,
        "symbol": symbol,
        "start_time": start_time,
        "end_time": end_time,
        "account_id": account_pair,
        "evidence_summary": (
            f"{account_pair} traded {trade_count} times on {symbol} with "
            f"net position ratio {net_position_ratio:.2%}."
        ),
        "recommended_follow_up": RECOMMENDED_FOLLOW_UP,
        "dedup_key": make_dedup_key(ALERT_TYPE, symbol, start_time, end_time, account_pair),
        "created_at": end_time,
        "evidence": [
            _evidence("trade_count", trade_count, MIN_PAIR_TRADES, ">=", "Trades between linked pair."),
            _evidence("notional_value", notional_value, MIN_NOTIONAL, ">=", "Total notional value."),
            _evidence(
                "net_position_ratio",
                net_position_ratio,
                MAX_NET_POSITION_RATIO,
                "<=",
                "Absolute net position change divided by total quantity.",
            ),
            _evidence(
                "link_confidence",
                link_confidence,
                LINK_CONFIDENCE_THRESHOLD,
                ">=",
                f"Account link type: {link_type}.",
            ),
        ],
    }


def _evidence(
    metric_name: str,
    metric_value: object,
    threshold_value: object,
    comparison_operator: str | None,
    explanation: str,
) -> dict[str, Any]:
    return {
        "metric_name": metric_name,
        "metric_value": float(metric_value) if pd.notna(metric_value) else None,
        "threshold_value": float(threshold_value) if threshold_value is not None else None,
        "comparison_operator": comparison_operator,
        "explanation": explanation,
    }


def _empty_alerts() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "alert_type",
            "severity",
            "severity_score",
            "exchange",
            "symbol",
            "start_time",
            "end_time",
            "account_id",
            "evidence_summary",
            "recommended_follow_up",
            "dedup_key",
            "created_at",
            "evidence",
        ]
    )
