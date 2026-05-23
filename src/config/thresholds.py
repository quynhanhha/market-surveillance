"""Centralized configuration values for synthetic data and detection."""

from __future__ import annotations

from datetime import UTC, datetime


RANDOM_SEED = 42
GENERATION_END = datetime(2026, 5, 23, tzinfo=UTC)
GENERATION_DAYS = 14

SYMBOL_BASE_PRICES = {
    "BTC/USDT": 68000.0,
    "ETH/USDT": 3600.0,
    "SOL/USDT": 165.0,
    "XRP/USDT": 0.62,
}

ACCOUNT_COUNTS = {
    "retail": 40,
    "active_retail": 20,
    "market_maker": 10,
    "institutional": 5,
    "suspicious": 8,
}

ORDER_SIZE_PARAMS = {
    "retail": {"mu": 2.0, "sigma": 0.8},
    "active_retail": {"mu": 3.0, "sigma": 0.7},
    "market_maker": {"mu": 1.5, "sigma": 0.4},
    "institutional": {"mu": 5.5, "sigma": 0.6},
}

CANCEL_RATE_RANGES = {
    "retail": (0.05, 0.15),
    "active_retail": (0.15, 0.25),
    "market_maker": (0.60, 0.80),
    "institutional": (0.03, 0.08),
    "suspicious": (0.15, 0.30),
}

FILL_RATE_RANGES = {
    "retail": (0.55, 0.75),
    "active_retail": (0.50, 0.70),
    "market_maker": (0.30, 0.50),
    "institutional": (0.70, 0.85),
    "suspicious": (0.50, 0.75),
}

LINK_CONFIDENCE_RANGES = {
    "shared_infrastructure": (0.60, 0.95),
    "coordinated_timing": (0.70, 0.90),
    "beneficial_ownership": (0.85, 0.99),
    "historical_pattern": (0.50, 0.75),
}

BASELINE_TRADE_COUNT = 4_200
BASELINE_CANCELLED_ORDER_COUNT = 1_800

WASH_ROUND_TRIPS_PER_PAIR = 10
WASH_SKIP_PROBABILITY = 0.20
WASH_MAX_NET_POSITION_RATIO = 0.08

SPOOF_EVENT_COUNT = 6
PUMP_BURST_COUNT = 4
