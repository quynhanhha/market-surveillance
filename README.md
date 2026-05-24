# Crypto Market Surveillance Analytics

Crypto markets move fast, but the abuse patterns that matter to exchanges and trading-risk teams are consistent: abnormal price shocks, volume anomalies, coordinated pump-and-dump behavior, wash trading, and spoofing or layering designed to mislead the market. This project is a surveillance dashboard that turns public market candles and synthetic account-level scenarios into explainable alerts, evidence packages, severity scores, and case reports that mirror the workflow an analyst or investigator would use in a real control environment.

Demo: https://crypto-market-surveillance.streamlit.app

## Project Overview

Crypto Market Surveillance Analytics is a Streamlit-based surveillance prototype for crypto exchange, compliance, and market-integrity teams. It combines public OHLCV market data with deterministic synthetic account and order activity to demonstrate how a surveillance stack can identify suspicious patterns, prioritize cases, and preserve evidence for follow-up.

The emphasis is not on generic analytics. It is on surveillance operations: alert generation, triage, severity ranking, deduplication, evidence capture, and case reporting.

## Why This Project Exists

Market abuse investigations require two different views of the market:

1. Public market behavior, such as price and volume shocks that can indicate manipulation or material news flow.
2. Account-level behavior, such as linked trading, rapid cancellations, and coordinated activity that can indicate intent.

Public exchange APIs provide the first view, but not the second. This project shows how a practical surveillance product can bridge that gap with a clear boundary between real market data and synthetic private-account scenarios.

## Demo Link

Live demo: https://crypto-market-surveillance.streamlit.app

The demo is deployed on Streamlit Community Cloud and may rebuild its local database from committed sample data after a cold start.

## Screenshots

- [screenshot: overview page]
- [screenshot: market anomalies page]
- [screenshot: synthetic surveillance cases page]
- [screenshot: alert detail page]
- [screenshot: daily report page]
- [screenshot: methodology page]

## Core Features

- Public OHLCV ingestion for BTC/USD, ETH/USD, and SOL/USD from Coinbase-compatible exchange data.
- Fallback to committed sample candles when the live API is unavailable.
- Deterministic synthetic accounts, account links, orders, and trades for private-account surveillance workflows.
- Five surveillance rules with explainable evidence and analyst follow-up guidance.
- Shared severity scoring so alerts are prioritized consistently across rule types.
- SQLite-backed alert, evidence, and case storage with deterministic deduplication.
- PDF case report generation for analyst review and handoff.
- Streamlit dashboard pages for overview, anomalies, synthetic cases, alert detail, daily report, and methodology.

## Architecture

```text
Public Exchange API or Sample Market Data
                 |
                 v
         Market Ingestion Layer
                 |
                 v
       SQLite Surveillance Database
                 |
        +--------+--------+
        |                 |
        v                 v
 Market Detection     Synthetic Scenario
  Rules + Severity     Detection Rules
        |                 |
        +--------+--------+
                 |
                 v
      Alerts, Evidence, and Cases
                 |
                 v
     Streamlit Dashboard and PDF Reports
```

The codebase keeps responsibilities separated: detection logic stays in `src/detection/`, threshold values stay in `src/config/thresholds.py`, database logic stays in `src/storage/`, and the UI only renders and routes the outputs.

## Data Sources

- Real market data: public OHLCV candles fetched from the exchange layer through CCXT-compatible ingestion.
- Sample market data: committed CSV candles used when live data cannot be fetched.
- Synthetic surveillance data: deterministic accounts, links, orders, and trades generated with `seed=42` to approximate realistic surveillance scenarios.
- Report data: alert records and evidence rows stored in SQLite and transformed into case reports.

## Real vs Synthetic Data Boundary

> Public exchange APIs expose market-level data but do not expose private
> account identifiers or full account-level order lifecycle data. This project
> uses real public market data for price/volume monitoring and synthetic
> account-level scenarios to demonstrate surveillance investigation workflows.
> The synthetic data is generated to approximate realistic account behavior,
> not random noise, but it does not represent real accounts or real transactions.

## Detection Rules

### 1. Price Anomaly

This rule watches each candle’s return against the recent baseline for that same market and timeframe. If a candle’s price move is more than three standard deviations away from the previous 24-candle pattern, it is flagged as unusual.

Severity is based on how statistically extreme the move is. The further the candle sits outside the normal range, the higher the score.

### 2. Volume Spike

This rule looks for candles where volume jumps far above normal trading activity. A candle is flagged when its volume is more than three standard deviations above the prior 24-candle baseline.

Severity increases when the spike is not just statistically unusual, but also materially large in absolute terms. In plain English: the alert is more serious when the surge is both abnormal and obviously big.

### 3. Pump-and-Dump Candidate

This rule looks for a short burst of upward price movement, abnormal volume, and then a quick reversal. In the implementation, the move must rise by at least 5%, show elevated volume, and then reverse by at least 3% within the reversal window.

Severity rises when more of the classic pump-and-dump pattern is present. A rise alone is not enough; the score gets stronger when the spike, the volume, the reversal, and corroborating alerts all line up.

### 4. Synthetic Wash Trading Pattern

This rule watches for linked accounts that trade back and forth repeatedly over a 48-hour window, with enough notional value to matter, but without changing their net position much. That is the classic signature of activity designed to create the appearance of trading interest.

Severity is driven by the number of repeated trades, the confidence in the account linkage, and the size of the notional traded. More repetition and stronger linkage mean a more serious alert.

### 5. Synthetic Spoofing/Layering Pattern

This rule looks for repeated large orders that are canceled very quickly, followed by opposite-side trades shortly afterward. That combination is consistent with attempts to move the market without genuine intent to execute the displayed orders.

Severity increases with repeated occurrences and higher total notional. The more often the pattern repeats, and the larger the orders involved, the more concerning the alert becomes.

## Severity Scoring

Alerts are assigned a numeric severity score and then mapped into a business-friendly label:

- `Low` for lower-confidence or narrower signals
- `Medium` for more credible or more material signals
- `High` for the most concerning patterns

The scoring model is intentionally shared across the rules so that analysts can compare alerts on the same scale. The score rewards factors such as:

- unusual statistical movement
- repeated suspicious behavior
- high notional value
- linked accounts or strong coordination signals
- rapid reversal or quick cancellation behavior
- confirmation from multiple rules

## Database Schema

The SQLite schema includes:

- `market_candles` for ingested public OHLCV data
- `alerts` for rule-generated surveillance alerts
- `alert_evidence` for the supporting metrics behind each alert
- `accounts` for synthetic account profiles
- `account_links` for synthetic relationship and linkage data
- `synthetic_orders` for account-level order activity
- `synthetic_trades` for matched trade activity
- `cases` for analyst follow-up and case tracking

Alert deduplication is deterministic so the same alert window does not create duplicate records.

## Deployment Constraints (SQLite / ephemeral filesystem)

> This application uses SQLite for local and demo deployments. Streamlit
> Community Cloud uses an ephemeral filesystem, so the database is rebuilt
> from committed sample data on each cold start. Live data fetched during a
> session is not persisted between sessions. For a production deployment,
> this layer would be replaced with a persistent database such as PostgreSQL.

## How to Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Testing

Run the project checks with:

```bash
python3 -m pytest
python3 -m ruff check .
```

These checks should confirm that:

- the detection rules fire on the intended synthetic and market scenarios
- deduplication prevents duplicate alert inserts
- deterministic synthetic data remains stable across runs
- fallback ingestion works when live market data is unavailable

## Limitations

- This is a surveillance prototype, not a production control room.
- Public market data cannot prove account ownership, coordination, or intent.
- Synthetic account activity is deliberately realistic, but it is still synthetic.
- SQLite is appropriate for local and demo use, but not for multi-user production scale.
- API availability and market coverage depend on the external exchange source.

## Future Work

- Replace SQLite with a persistent production database.
- Add richer case management and analyst workflow controls.
- Integrate more exchange venues and deeper market coverage.
- Extend entity resolution and linkage analysis for account networks.
- Add feedback loops so analyst dispositions can improve prioritization over time.

## What This Demonstrates

- Built a crypto market surveillance workflow that separates public market monitoring from private-account abuse scenarios.
- Implemented explainable detection logic for price anomalies, volume spikes, pump-and-dump patterns, wash trading, and spoofing or layering.
- Designed a shared severity model, evidence capture, and deduplicated alert storage to support analyst triage.
- Delivered a Streamlit-based interface with alert review, case reporting, and operational context suitable for risk and compliance stakeholders.
- Documented deployment constraints honestly, including the real-versus-synthetic data boundary and the limits of an ephemeral SQLite demo environment.
