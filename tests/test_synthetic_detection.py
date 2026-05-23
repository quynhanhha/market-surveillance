"""Synthetic data generation tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.config.thresholds import (
    ACCOUNT_COUNTS,
    GENERATION_END,
    PUMP_BURST_COUNT,
    RANDOM_SEED,
    SPOOF_EVENT_COUNT,
    WASH_MAX_NET_POSITION_RATIO,
)
from src.ingestion.synthetic_data import (
    PUMP_ACCOUNTS,
    SPOOF_ACCOUNT,
    WASH_PAIRS,
    export_synthetic_data,
    generate_synthetic_dataset,
)


def test_synthetic_generation_is_deterministic() -> None:
    """The same seed must generate exactly the same data."""
    first = generate_synthetic_dataset(seed=RANDOM_SEED)
    second = generate_synthetic_dataset(seed=RANDOM_SEED)

    assert first.keys() == second.keys()
    for table_name in first:
        pd.testing.assert_frame_equal(first[table_name], second[table_name])


def test_account_mix_and_row_counts() -> None:
    """Generated tables match the Milestone 2 volume targets."""
    dataset = generate_synthetic_dataset()
    accounts = dataset["accounts"]
    links = dataset["account_links"]
    orders = dataset["synthetic_orders"]
    trades = dataset["synthetic_trades"]

    assert len(accounts) == sum(ACCOUNT_COUNTS.values()) == 83
    assert accounts["account_type"].value_counts().to_dict() == ACCOUNT_COUNTS
    assert 20 <= len(links) <= 35
    assert 8_000 <= len(orders) <= 15_000
    assert 3_000 <= len(trades) <= 6_000
    assert set(orders["status"]) == {"filled", "cancelled"}


def test_wash_trading_scenario_is_embedded() -> None:
    """Wash pairs have links, repeated trades, and low net position change."""
    dataset = generate_synthetic_dataset()
    links = dataset["account_links"]
    trades = dataset["synthetic_trades"]
    start = GENERATION_END - timedelta(days=5)
    end = start + timedelta(hours=48)

    for account_a, account_b in WASH_PAIRS:
        link = links[
            (links["account_id_a"] == min(account_a, account_b))
            & (links["account_id_b"] == max(account_a, account_b))
        ].iloc[0]
        assert link["link_type"] == "beneficial_ownership"
        assert link["confidence"] >= 0.90

        pair_trades = trades[
            (trades["symbol"] == "ETH/USDT")
            & (pd.to_datetime(trades["timestamp"], utc=True) >= start)
            & (pd.to_datetime(trades["timestamp"], utc=True) <= end)
            & (
                (
                    (trades["buyer_account_id"] == account_a)
                    & (trades["seller_account_id"] == account_b)
                )
                | (
                    (trades["buyer_account_id"] == account_b)
                    & (trades["seller_account_id"] == account_a)
                )
            )
        ]
        assert len(pair_trades) >= 10
        bought = pair_trades.loc[pair_trades["buyer_account_id"] == account_a, "quantity"].sum()
        sold = pair_trades.loc[pair_trades["seller_account_id"] == account_a, "quantity"].sum()
        total = pair_trades["quantity"].sum()
        assert abs(bought - sold) / total < WASH_MAX_NET_POSITION_RATIO


def test_spoofing_layering_scenario_is_embedded() -> None:
    """Spoofing account has repeated large cancellations and opposite trades."""
    dataset = generate_synthetic_dataset()
    orders = dataset["synthetic_orders"]
    trades = dataset["synthetic_trades"]
    start = GENERATION_END - timedelta(days=3, hours=6)
    end = start + timedelta(hours=6)
    order_times = pd.to_datetime(orders["timestamp"], utc=True)
    trade_times = pd.to_datetime(trades["timestamp"], utc=True)

    cancelled = orders[
        (orders["account_id"] == SPOOF_ACCOUNT)
        & (orders["symbol"] == "BTC/USDT")
        & (orders["status"] == "cancelled")
        & (order_times >= start)
        & (order_times <= end)
    ]
    assert len(cancelled) >= SPOOF_EVENT_COUNT * 3
    cancel_seconds = (
        pd.to_datetime(cancelled["cancelled_at"], utc=True)
        - pd.to_datetime(cancelled["submitted_at"], utc=True)
    ).dt.total_seconds()
    assert cancel_seconds.median() <= 45

    opposite_trades = trades[
        (trades["symbol"] == "BTC/USDT")
        & (trade_times >= start)
        & (trade_times <= end + timedelta(minutes=5))
        & (
            (trades["buyer_account_id"] == SPOOF_ACCOUNT)
            | (trades["seller_account_id"] == SPOOF_ACCOUNT)
        )
    ]
    assert len(opposite_trades) >= SPOOF_EVENT_COUNT


def test_pump_pressure_scenario_is_embedded() -> None:
    """Coordinated pump accounts buy in tight repeated bursts."""
    dataset = generate_synthetic_dataset()
    links = dataset["account_links"]
    trades = dataset["synthetic_trades"]
    start = GENERATION_END - timedelta(days=2, hours=12)

    pump_links = links[
        (links["account_id_a"].isin(PUMP_ACCOUNTS))
        & (links["account_id_b"].isin(PUMP_ACCOUNTS))
        & (links["link_type"] == "coordinated_timing")
    ]
    assert len(pump_links) == 6

    for burst_index in range(PUMP_BURST_COUNT):
        burst_start = start + timedelta(hours=burst_index * 3)
        burst_end = burst_start + timedelta(seconds=90)
        burst = trades[
            (trades["symbol"] == "SOL/USDT")
            & (trades["buyer_account_id"].isin(PUMP_ACCOUNTS))
            & (pd.to_datetime(trades["timestamp"], utc=True) >= burst_start)
            & (pd.to_datetime(trades["timestamp"], utc=True) <= burst_end)
        ]
        assert set(burst["buyer_account_id"]) == set(PUMP_ACCOUNTS)


def test_export_writes_deterministic_sample_files(tmp_path: Path) -> None:
    """CSV export uses the same seeded generator."""
    paths = export_synthetic_data(output_dir=tmp_path, seed=RANDOM_SEED)

    assert set(paths) == {
        "accounts",
        "account_links",
        "synthetic_orders",
        "synthetic_trades",
    }
    accounts = pd.read_csv(paths["accounts"])
    orders = pd.read_csv(paths["synthetic_orders"])
    assert len(accounts) == 83
    assert len(orders) >= 8_000


def test_generated_timestamps_use_fixed_clock() -> None:
    """Generation must not depend on the current wall clock."""
    dataset = generate_synthetic_dataset()
    max_timestamp = pd.to_datetime(dataset["synthetic_orders"]["timestamp"], utc=True).max()
    assert max_timestamp.to_pydatetime() <= datetime(2026, 5, 23, tzinfo=UTC)
