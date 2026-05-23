"""SQLite schema initialization tests."""

from __future__ import annotations

import sqlite3

from src.storage.db import connect_sqlite
from src.storage.schema import create_schema
from src.ingestion.synthetic_data import generate_synthetic_dataset


def test_create_schema_adds_all_required_tables() -> None:
    """Section 9 tables are created in SQLite."""
    conn = connect_sqlite()
    create_schema(conn)

    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    table_names = {row["name"] for row in rows}

    assert {
        "market_candles",
        "alerts",
        "alert_evidence",
        "accounts",
        "account_links",
        "synthetic_orders",
        "synthetic_trades",
        "cases",
    }.issubset(table_names)


def test_synthetic_tables_have_section_9_columns() -> None:
    """Generated data tables match the storage schema columns."""
    conn = connect_sqlite()
    create_schema(conn)

    order_columns = table_columns(conn, "synthetic_orders")
    trade_columns = table_columns(conn, "synthetic_trades")

    assert order_columns == {
        "order_id",
        "timestamp",
        "account_id",
        "symbol",
        "side",
        "price",
        "quantity",
        "status",
        "submitted_at",
        "cancelled_at",
        "filled_at",
    }
    assert trade_columns == {
        "trade_id",
        "timestamp",
        "symbol",
        "buyer_account_id",
        "seller_account_id",
        "price",
        "quantity",
        "notional_value",
    }


def test_generated_synthetic_data_loads_into_schema() -> None:
    """Generated synthetic sample tables are compatible with SQLite schema."""
    conn = connect_sqlite()
    create_schema(conn)
    dataset = generate_synthetic_dataset()

    dataset["accounts"].to_sql("accounts", conn, if_exists="append", index=False)
    dataset["account_links"].to_sql(
        "account_links", conn, if_exists="append", index=False
    )
    dataset["synthetic_orders"].to_sql(
        "synthetic_orders", conn, if_exists="append", index=False
    )
    dataset["synthetic_trades"].to_sql(
        "synthetic_trades", conn, if_exists="append", index=False
    )

    assert conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 83
    assert conn.execute("SELECT COUNT(*) FROM synthetic_trades").fetchone()[0] >= 3_000


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    """Return user-defined columns for a table."""
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})")}
