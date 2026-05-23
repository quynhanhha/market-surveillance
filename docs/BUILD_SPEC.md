# Build Spec: Crypto Market Surveillance Analytics
---

## 0. Project Identity

### Project name

**Crypto Market Surveillance Analytics**

### One-line description

A deployed SQL/Python monitoring prototype that ingests live public crypto market data, detects abnormal price-volume behavior, generates surveillance alerts, and supports case-style investigation reporting.

### Portfolio positioning

This project demonstrates the ability to build operational analytics tooling for market surveillance, risk control, trading operations, and transaction-monitoring workflows.

It is designed to prove:

- SQL/Python data analysis
- market monitoring
- anomaly detection
- alert generation
- investigation workflow design
- clear reporting
- production-aware engineering judgment

This is **not** a trading bot.
This is **not** a crypto portfolio tracker.
This is **not** "AI fraud detection."

It is a surveillance analytics prototype.

---

## 1. Target Role Alignment

This project is built for roles asking for:

- market surveillance
- trading risk control
- transaction monitoring
- abnormal transaction analysis
- alert triage
- risk reports
- suspicious activity investigation
- SQL/Python/Excel data analysis
- pattern detection
- market manipulation awareness
- collaboration with risk/product/technical teams

The target reviewer should immediately infer:

> This candidate can support a monitoring workflow: ingest trading data, detect abnormal behavior, classify alerts, document evidence, and communicate findings.

---

## 2. Target User

### Primary user

A junior market surveillance or risk operations analyst.

### User workflow

The analyst needs to:

1. View latest market activity.
2. Identify abnormal symbols or trading windows.
3. Review triggered alerts.
4. Understand why each alert fired.
5. Inspect supporting evidence.
6. Classify or escalate the case.
7. Generate a concise investigation summary.

### User questions the app must answer

- What alerts fired recently?
- Which symbols had abnormal price or volume movement?
- Which alerts are highest severity?
- What evidence supports each alert?
- Is this likely noise, a candidate issue, or worth escalation?
- What should be recorded in the case report?
- What data limitations apply?

---

## 3. Scope Decision

### Version 1 scope

V1 is a **live-data-backed, near-real-time surveillance analytics dashboard**.

It will support:

- manual refresh of latest market data
- optional timed refresh in the dashboard
- batch anomaly detection
- alert persistence with deduplication
- realistic synthetic account-level surveillance scenarios
- investigation report generation
- public deployment via Streamlit Community Cloud

### Explicitly out of scope for V1

- WebSocket streaming ingestion
- user authentication
- paid API integrations
- full backend API
- React frontend
- Kafka / event queues
- ML models
- actual manipulation accusations
- production compliance system
- real account-level exchange surveillance

---

## 4. Data Strategy

### 4.1 Real public market data

Use public exchange market data for:

- OHLCV candles
- price returns
- volume changes
- volatility
- symbol-level anomaly detection
- pump-and-dump candidate detection

Recommended data access: **CCXT** against Binance or Coinbase.

#### Real market data table: `market_candles`

| Field      | Type        | Notes                  |
|------------|-------------|------------------------|
| id         | INTEGER PK  | internal row id        |
| exchange   | TEXT        | e.g. binance           |
| symbol     | TEXT        | e.g. BTC/USDT          |
| timeframe  | TEXT        | e.g. 1m, 5m            |
| timestamp  | TEXT        | candle open time (ISO) |
| open       | REAL        | candle open            |
| high       | REAL        | candle high            |
| low        | REAL        | candle low             |
| close      | REAL        | candle close           |
| volume     | REAL        | traded volume          |
| fetched_at | TEXT        | ingestion timestamp    |

Unique constraint:

```sql
UNIQUE(exchange, symbol, timeframe, timestamp)
```

### 4.2 Synthetic account-level data

Synthetic data supports workflows that public market APIs cannot expose:

- account correlations
- wash trading
- linked-account trading
- spoofing/layering approximations
- case-handling workflow

Synthetic data is **not** random noise. It is generated to approximate realistic
account behavior — plausible order sizes, realistic timing distributions,
account relationship structures that mirror how these patterns actually manifest.
See Section 5 for the full synthetic data generation specification.

The README must explicitly state:

> Public exchange APIs expose market-level data but do not expose private account
> identifiers or full account-level order lifecycle data. This project uses real
> public market data for price/volume monitoring and synthetic account-level
> scenarios to demonstrate surveillance investigation workflows. The synthetic
> data is generated to approximate realistic account behavior, not random noise,
> but it does not represent real accounts or real transactions.

---

## 5. Synthetic Data Generation Specification

This section is new and required. Synthetic data that looks obviously fake
undermines the portfolio signal. The goal is behavioral plausibility — patterns
that a real surveillance analyst would find worth reviewing.

### 5.1 Design principles

- All generation is **seeded and deterministic** (`random.seed(42)`, `numpy.random.seed(42)`).
- Parameters are centralized in `config/thresholds.py`, not scattered.
- Accounts have realistic **behavioral profiles** that drive their order patterns.
- Suspicious scenarios are **embedded within a realistic baseline** of normal activity.
  A wash trading pair should not be the only accounts trading. They should exist
  inside a population of accounts with varied, plausible behavior.
- Time distributions follow realistic patterns: activity clusters around
  market-active hours, order sizes follow log-normal distributions, cancellation
  rates vary by account type.

### 5.2 Account population

Generate a mixed population of account types.

#### Account types and behavioral profiles

| Account type   | Description                                                                 | Order size dist.         | Cancel rate | Activity pattern             |
|----------------|-----------------------------------------------------------------------------|--------------------------|-------------|------------------------------|
| `retail`       | Small traders. Irregular activity, small sizes, low cancel rate.            | Log-normal, small mean   | 5–15%       | Random, sparse               |
| `active_retail`| Frequent traders. Higher volume, moderate cancel rate.                      | Log-normal, medium mean  | 15–25%      | Multiple sessions/day        |
| `market_maker` | High frequency, symmetric buy/sell, frequent cancellations, tight sizes.    | Uniform, small tight     | 60–80%      | Continuous, clustered        |
| `institutional`| Large infrequent orders. Low cancel rate, high notional.                    | Log-normal, large mean   | 3–8%        | Sparse, business hours       |
| `suspicious`   | Accounts involved in synthetic manipulation scenarios.                      | Scenario-dependent       | Scenario-dependent | Scenario-dependent    |

Generate approximately:

- 40 retail accounts
- 20 active_retail accounts
- 10 market_maker accounts
- 5 institutional accounts
- 6–10 suspicious accounts (embedded in scenarios)

Total: approximately 75–85 accounts. Large enough to make suspicious accounts
non-obvious by inspection alone.

#### Account fields

```python
account_id: str          # e.g. "ACC_0042"
account_type: str
created_at: str          # ISO datetime, randomized over past 18 months
risk_tier: str           # Low / Medium / High
jurisdiction: str        # synthetic, e.g. "Region_A", "Region_B"
avg_daily_volume: float  # baseline for behavioral comparison
```

`risk_tier` is assigned by account type:

- retail → Low or Medium (80/20)
- active_retail → Medium or High (60/40)
- market_maker → Medium
- institutional → Low or Medium (70/30)
- suspicious → High

### 5.3 Account linkage

Account links represent relationships that a real surveillance system might
infer or know — shared infrastructure, coordinated behavior, known associations.

#### Link types

| Link type            | Meaning                                                   | Confidence range |
|----------------------|-----------------------------------------------------------|-----------------|
| `shared_infrastructure` | Accounts from same IP range / device fingerprint      | 0.60–0.95       |
| `coordinated_timing` | Orders placed within milliseconds of each other consistently | 0.70–0.90  |
| `beneficial_ownership` | Known or inferred shared ownership                    | 0.85–0.99       |
| `historical_pattern` | Prior co-occurrence in flagged activity                   | 0.50–0.75       |

Generate links only between suspicious accounts and optionally between a small
number of non-suspicious accounts (5–8 pairs) to prevent linkage being a
trivially obvious signal.

### 5.4 Order and trade generation

#### Order timing

Orders are not uniformly distributed over time. Use a mixture model:

- 60% of daily activity clustered in two 3-hour windows (simulating opening
  and afternoon sessions)
- 30% spread across remaining hours
- 10% sparse overnight/off-hours

Jitter timestamps within windows using a truncated normal distribution
(mean = window midpoint, std = 45 minutes).

#### Order sizes

Use log-normal distributions parameterized by account type:

```python
ORDER_SIZE_PARAMS = {
    "retail":        {"mu": 2.0, "sigma": 0.8},   # ~7 units mean
    "active_retail": {"mu": 3.0, "sigma": 0.7},   # ~20 units mean
    "market_maker":  {"mu": 1.5, "sigma": 0.4},   # ~4.5 units mean, tight
    "institutional": {"mu": 5.5, "sigma": 0.6},   # ~245 units mean
}
```

Prices are set relative to a synthetic baseline price for each symbol,
with small random walk perturbations to simulate realistic price movement.

#### Trade generation

Trades are generated from filled orders. Not all orders fill — fill rate
varies by account type and order type:

- market_maker: 30–50% fill rate (many cancelled)
- retail: 55–75% fill rate
- institutional: 70–85% fill rate

Trades require a buyer and seller. Match filled buy orders to filled sell
orders within a short time window (±2 minutes), prioritizing same-symbol
matches. Unmatched fills can be assigned a synthetic counterparty from the
market_maker pool.

### 5.5 Scenario generation

Each scenario is a self-contained function in `ingestion/synthetic_data.py`
that injects a specific pattern into the account/order/trade population.

#### Scenario 1: Wash trading pair

Two accounts (linked by `beneficial_ownership`, confidence 0.90+) repeatedly
trade the same symbol back and forth over a 48-hour window.

Realistic constraints:

- They do not trade exclusively with each other. Each account also has a
  realistic baseline of normal trades with non-linked counterparties.
- Order sizes vary slightly between round trips (±5–10%) to avoid identical
  notional values that would be trivially detectable.
- They occasionally skip a round trip (20% probability per cycle) to simulate
  imperfect coordination.
- The net position change per account over the window is less than 8% of total
  notional, consistent with the economic purpose being artificial volume rather
  than directional exposure.
- Timing between paired orders varies: some pairs are placed within 30 seconds,
  others within 10 minutes, to approximate realistic coordination noise.

Injection volume: 8–12 round trips per pair, 2 pairs per scenario run.

#### Scenario 2: Spoofing / layering

One account (or two linked accounts operating in coordination) places a series
of large orders on one side, cancels them quickly, then executes smaller orders
on the opposite side.

Realistic constraints:

- Large orders are 4–8× the account's own historical average order size,
  not a fixed multiplier against the population.
- Cancellation times follow a short log-normal distribution: most cancelled
  within 15–45 seconds, a few within 5 minutes (to approximate partial
  detection avoidance).
- The opposite-side trade occurs within 1–3 minutes of the last cancellation.
- The account also has normal baseline activity around the spoofing events —
  the suspicious events are embedded, not isolated.
- The pattern repeats 4–7 times over a 6-hour window with varying intervals.

#### Scenario 3: Coordinated pump pressure (synthetic market-level)

Three to four accounts (linked by `coordinated_timing`) place buy orders in the
same symbol within short windows, creating synthetic upward pressure. No sell
coordination is modeled (that would require market impact simulation out of
scope for V1).

Realistic constraints:

- Accounts place orders within 90-second windows of each other, but not
  simultaneously (coordination with noise).
- Order sizes are elevated relative to each account's baseline but not
  extreme — 2–3× normal, not 10×.
- The pattern occurs in 3–5 bursts over a 12-hour window.
- Used in conjunction with real market data where a price spike occurred,
  to simulate what account-level data might look like alongside a real anomaly.

### 5.6 Synthetic data volume targets

| Table              | Target rows              |
|--------------------|--------------------------|
| accounts           | 75–85                    |
| account_links      | 20–35                    |
| synthetic_orders   | 8,000–15,000             |
| synthetic_trades   | 3,000–6,000              |

This volume is sufficient to make pattern detection non-trivial and
dashboards non-empty, without requiring large file storage in the repo.

### 5.7 Committed sample data

Committed sample data files in `data/` must be generated from the same seeded
functions. They are not hand-crafted. Running `python src/ingestion/synthetic_data.py`
with `--export` regenerates them deterministically.

---

## 6. System Architecture

### 6.1 High-level architecture

```
Exchange API / CCXT
        |
        v
Market Data Ingestion
        |
        v
SQLite Storage
        |
        v
Detection Engine
        |
        v
Alerts + Evidence (with deduplication)
        |
        v
Streamlit Dashboard
        |
        v
Case Report Generator
```

### 6.2 Deployment architecture

```
GitHub Repo
    |
    v
Streamlit Community Cloud
    |
    v
Public Demo Link
```

### 6.3 Runtime mode and SQLite deployment constraint

**This section is required reading before building the ingestion layer.**

Streamlit Community Cloud uses an **ephemeral filesystem**. The SQLite database
file does not persist between cold starts or dyno restarts. This is a real
architectural constraint, not a minor footnote.

Practical consequences:

- On every cold start, the database is recreated from schema + committed sample data.
- Live market data fetched during a session is ingested into that session's
  in-memory database. It does not persist after the session ends.
- Alerts generated from live data exist only for the session duration.

The app handles this as follows:

1. On startup: initialize SQLite schema, seed from committed sample data.
2. On refresh: fetch live data via CCXT, insert into session database, run
   detection, display results.
3. On API failure: display committed sample data with clear "sample data" label.

**The dashboard must always display a prominent data source indicator:**

```
Data source: [Live — last fetched 14:32 UTC] or [Sample data — API unavailable]
```

**The README must explicitly state:**

> This application uses SQLite for local and demo deployments. Streamlit Community
> Cloud uses an ephemeral filesystem, so the database is rebuilt from committed
> sample data on each cold start. Live data fetched during a session is not
> persisted between sessions. For a production deployment, this layer would be
> replaced with a persistent database such as PostgreSQL.

This framing is honest and signals production awareness. Do not omit it.

---

## 7. Tech Stack

### Core stack

- Python 3.11+
- pandas
- numpy
- SQLite
- SQLAlchemy or `sqlite3`
- Streamlit
- Plotly or Altair
- CCXT
- pytest
- ruff
- mypy (optional but preferred)

### Deployment

- GitHub (public repo)
- Streamlit Community Cloud

### Dependency management

Use `requirements.txt`.

```
streamlit
pandas
numpy
plotly
ccxt
sqlalchemy
pytest
ruff
python-dotenv
```

---

## 8. Repository Structure

```
crypto-market-surveillance/
  README.md
  requirements.txt
  .gitignore
  app.py

  src/
    __init__.py

    config/
      settings.py
      thresholds.py

    ingestion/
      __init__.py
      fetch_market_data.py
      synthetic_data.py

    storage/
      __init__.py
      db.py
      schema.py
      repositories.py

    detection/
      __init__.py
      price_anomaly.py
      volume_spike.py
      pump_dump.py
      wash_trading.py
      spoofing_layering.py
      severity.py

    reporting/
      __init__.py
      case_report.py
      daily_summary.py

    ui/
      __init__.py
      components.py
      charts.py
      pages.py

    utils/
      __init__.py
      time.py
      logging.py
      validation.py

  sql/
    create_tables.sql
    detect_price_anomalies.sql
    detect_volume_spikes.sql
    detect_pump_dump_candidates.sql
    detect_wash_trading_synthetic.sql
    detect_spoofing_layering_synthetic.sql

  data/
    sample_market_candles.csv
    sample_synthetic_orders.csv
    sample_synthetic_trades.csv
    sample_alerts.csv

  tests/
    test_price_anomaly.py
    test_volume_spike.py
    test_pump_dump.py
    test_synthetic_detection.py
    test_case_report.py
    test_alert_dedup.py

  docs/
    screenshots/
    example_case_report.md
    architecture.md
    limitations.md
```

---

## 9. Database Schema

### 9.1 `market_candles`

```sql
CREATE TABLE IF NOT EXISTS market_candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    fetched_at TEXT NOT NULL,
    UNIQUE(exchange, symbol, timeframe, timestamp)
);
```

### 9.2 `alerts`

```sql
CREATE TABLE IF NOT EXISTS alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    severity_score INTEGER NOT NULL,
    exchange TEXT,
    symbol TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'New',
    evidence_summary TEXT NOT NULL,
    recommended_follow_up TEXT,
    dedup_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(dedup_key)
);
```

`severity_score` stores the numeric score (0–100) that produced the severity
classification. This makes the scoring transparent in the UI and queryable.

`dedup_key` is a deterministic hash used to prevent duplicate alerts across
detection runs. See Section 10.3.

Valid statuses: `New`, `Under Review`, `Escalated`, `Closed`

Valid severities: `Low`, `Medium`, `High`

### 9.3 `alert_evidence`

```sql
CREATE TABLE IF NOT EXISTS alert_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    threshold_value REAL,
    comparison_operator TEXT,
    explanation TEXT NOT NULL,
    FOREIGN KEY(alert_id) REFERENCES alerts(alert_id)
);
```

### 9.4 `accounts`

```sql
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    account_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    risk_tier TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    avg_daily_volume REAL NOT NULL
);
```

### 9.5 `account_links`

```sql
CREATE TABLE IF NOT EXISTS account_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id_a TEXT NOT NULL,
    account_id_b TEXT NOT NULL,
    link_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    FOREIGN KEY(account_id_a) REFERENCES accounts(account_id),
    FOREIGN KEY(account_id_b) REFERENCES accounts(account_id)
);
```

### 9.6 `synthetic_orders`

```sql
CREATE TABLE IF NOT EXISTS synthetic_orders (
    order_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    account_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    quantity REAL NOT NULL,
    status TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    cancelled_at TEXT,
    filled_at TEXT,
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);
```

### 9.7 `synthetic_trades`

```sql
CREATE TABLE IF NOT EXISTS synthetic_trades (
    trade_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    buyer_account_id TEXT NOT NULL,
    seller_account_id TEXT NOT NULL,
    price REAL NOT NULL,
    quantity REAL NOT NULL,
    notional_value REAL NOT NULL,
    FOREIGN KEY(buyer_account_id) REFERENCES accounts(account_id),
    FOREIGN KEY(seller_account_id) REFERENCES accounts(account_id)
);
```

### 9.8 `cases`

```sql
CREATE TABLE IF NOT EXISTS cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    case_status TEXT NOT NULL,
    analyst_note TEXT,
    classification TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(alert_id) REFERENCES alerts(alert_id)
);
```

---

## 10. Detection Rules and Severity

**Important:** There is one severity scoring system. Rule-level severity
descriptions are defined in terms of score ranges, which map to the same
Low/Medium/High thresholds used globally. Do not implement separate
per-rule severity logic alongside the central scoring system —
that produces two systems that silently disagree.

### 10.1 Unified severity scoring

Each alert is assigned a numeric score from 0–100. Severity maps from score:

```python
if score >= 75:
    severity = "High"
elif score >= 45:
    severity = "Medium"
else:
    severity = "Low"
```

Score is built from additive signal components. Each component is defined in
`detection/severity.py` and applied consistently across all rule types.

#### Scoring components

| Signal                              | Points |
|-------------------------------------|--------|
| Primary metric z-score 3–4          | +15    |
| Primary metric z-score 4–6          | +25    |
| Primary metric z-score > 6          | +40    |
| Repeated events (≥ 3 occurrences)   | +20    |
| Linked accounts confirmed           | +20    |
| High notional value                 | +15    |
| Multiple detection rules triggered  | +25    |
| Rapid price reversal confirmed      | +15    |
| High link confidence (> 0.85)       | +10    |

A single rule with z-score 3–4 and no other signals scores 15 → Low.
A single rule with z-score > 6 scores 40 → Low (just under Medium).
Z-score > 6 plus one other signal (e.g. repeated events) scores 60 → Medium.
This is intentional: extreme anomalies without corroboration are Medium at most
from market data alone. Cross-rule confirmation or account linkage is required
for High severity.

This model is transparent, auditable, and consistent.

### 10.2 Detection rules

#### Rule 1: Volume Spike

**Input:** `market_candles`

**Logic:**
- compute rolling mean volume over previous N windows
- compute rolling standard deviation
- compute volume z-score for each candle
- trigger if z-score exceeds threshold

**Default parameters:**
```python
ROLLING_WINDOW = 24
VOLUME_Z_THRESHOLD = 3.0
MIN_VOLUME_MULTIPLIER = 2.5
```

**Alert type:** `Volume Spike`

**Score contribution from this rule:**
- z-score 3–4: +15
- z-score 4–6: +25
- z-score > 6: +40
- add +15 if volume multiplier also exceeds MIN_VOLUME_MULTIPLIER (corroboration)

**Evidence fields:**
- current volume
- rolling mean volume
- volume z-score
- volume multiplier
- symbol, time window

---

#### Rule 2: Price Anomaly

**Input:** `market_candles`

**Logic:**
- compute candle return: `(close - open) / open`
- compute rolling mean return and standard deviation
- compute return z-score
- trigger if absolute z-score exceeds threshold

**Default parameters:**
```python
RETURN_Z_THRESHOLD = 3.0
ROLLING_WINDOW = 24
```

**Alert type:** `Price Anomaly`

**Score contribution:**
- absolute z-score 3–4: +15
- absolute z-score 4–6: +25
- absolute z-score > 6: +40

**Evidence fields:**
- return percentage
- rolling average return
- return z-score
- open/close price, candle timestamp

---

#### Rule 3: Pump-and-Dump Candidate

**Input:** `market_candles`

**Logic:**
1. price increases above threshold within pump window
2. volume exceeds rolling baseline (z-score threshold)
3. price reverses downward within reversal window

All three conditions must be met to trigger.

**Default parameters:**
```python
PUMP_RETURN_THRESHOLD = 0.05
VOLUME_Z_THRESHOLD = 3.0
REVERSAL_THRESHOLD = -0.03
PUMP_WINDOW = 3
REVERSAL_WINDOW = 6
```

**Alert type:** `Pump-and-Dump Candidate`

**Score contribution:**
- pump return 5–8%: +15
- pump return > 8%: +25
- volume z-score > 3: +15
- rapid reversal confirmed: +15
- all three conditions met simultaneously: +10 (corroboration bonus)

A clean pump-and-dump candidate with moderate values scores ~55 → Medium.
With extreme values it reaches 65 → Medium. Cross-rule confirmation with a
Volume Spike alert on the same symbol/window adds +25 → High.

**Evidence fields:**
- pump window return, peak price, reversal return
- volume z-score
- start/peak/reversal timestamps

---

#### Rule 4: Synthetic Wash Trading

**Input:** `synthetic_trades`, `account_links`

**Logic:**
- for each account pair and symbol in a rolling time window:
  - count trades between the pair
  - compute total notional value
  - compute net position change per account
  - check link existence and confidence
- trigger if: trade count ≥ threshold AND notional ≥ threshold
  AND net position ratio ≤ threshold AND link confidence ≥ threshold

**Default parameters:**
```python
MIN_PAIR_TRADES = 5
MIN_NOTIONAL = 50000
MAX_NET_POSITION_RATIO = 0.10
LINK_CONFIDENCE_THRESHOLD = 0.70
TIME_WINDOW_HOURS = 48
```

**Alert type:** `Synthetic Wash Trading Pattern`

**Score contribution:**
- pair trade count 5–9: +15
- pair trade count ≥ 10: +25
- linked accounts confirmed: +20
- link confidence > 0.85: +10
- high notional: +15

A minimal trigger (5 trades, confirmed link, moderate notional) scores ~50 → Medium.
With high trade count, high confidence, and high notional: ~70 → Medium/High boundary.

**Evidence fields:**
- account pair, trade count, notional value
- net position ratio, link type, link confidence
- symbol, time window

---

#### Rule 5: Synthetic Spoofing / Layering

**Input:** `synthetic_orders`, `synthetic_trades`

**Logic:**
- for each account:
  - identify orders that are large relative to that account's own historical
    average (not population average)
  - check cancellation time ≤ threshold
  - check whether opposite-side trade occurs within window after cancellation
  - count repeated instances
- trigger if repeated count ≥ threshold

**Default parameters:**
```python
LARGE_ORDER_MULTIPLIER = 4.0     # relative to account's own avg order size
MAX_CANCEL_SECONDS = 60
OPPOSITE_TRADE_WINDOW_SECONDS = 180
MIN_REPEATED_EVENTS = 3
```

Note: `LARGE_ORDER_MULTIPLIER` applies against the individual account's
`avg_daily_volume / avg_orders_per_day`, not a population mean.
This is more realistic and avoids flagging institutional accounts
simply for being large.

**Alert type:** `Synthetic Spoofing/Layering Pattern`

**Score contribution:**
- repeated events 3–5: +15
- repeated events > 5: +25
- linked account coordination confirmed: +20
- high notional: +15

**Evidence fields:**
- account ID, number of large cancelled orders
- average cancellation time
- opposite-side trades, symbol, time window

### 10.3 Alert deduplication

This is a required feature, not optional.

The detection engine runs on every manual or auto refresh. Without
deduplication, the same anomaly window generates a new alert record on
every run. The alerts table becomes meaningless.

#### Dedup key construction

Each alert must produce a deterministic `dedup_key` before insertion.

```python
import hashlib

def make_dedup_key(
    alert_type: str,
    symbol: str | None,
    start_time: str,
    end_time: str,
    account_id: str | None = None,
) -> str:
    raw = f"{alert_type}|{symbol or ''}|{start_time}|{end_time}|{account_id or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
```

The key is based on what makes an alert instance unique:
alert type + subject (symbol or account) + time window.

#### Insertion behavior

```sql
INSERT INTO alerts (...)
VALUES (...)
ON CONFLICT(dedup_key) DO NOTHING;
```

If the alert already exists, the insertion is silently skipped.
The existing alert record — including any analyst status updates — is preserved.

This means an analyst who marks an alert "Under Review" will not have that
status overwritten on the next detection run.

#### Alert freshness

The `created_at` field represents when the alert was first generated.
It does not update on subsequent detection runs. If you need to track
when an alert was last seen, add a `last_seen_at` column:

```sql
ALTER TABLE alerts ADD COLUMN last_seen_at TEXT;
```

Update it on conflict:

```sql
INSERT INTO alerts (...)
VALUES (...)
ON CONFLICT(dedup_key) DO UPDATE SET last_seen_at = excluded.created_at;
```

This is optional for V1 but useful for distinguishing stale from active alerts.

#### Time window bucketing

For market-data rules (volume spike, price anomaly), `start_time` and
`end_time` should be bucketed to the candle's timeframe boundary, not
the exact detection timestamp. Otherwise two runs that detect the same
candle will produce different keys because `fetched_at` differs.

```python
# Correct: use candle timestamp
start_time = candle_timestamp
end_time = candle_timestamp  # for single-candle alerts

# Wrong: use current time
start_time = datetime.utcnow().isoformat()  # breaks dedup
```

#### Tests

`tests/test_alert_dedup.py` must cover:

- same alert run twice → one record in database
- different symbol same type → two records
- analyst status preserved on second run
- dedup key is deterministic across processes

---

## 11. UI Specification

### 11.1 App layout

Streamlit multi-page or sidebar navigation.

Pages:

1. Overview
2. Market Anomalies
3. Synthetic Surveillance Cases
4. Alert Detail
5. Daily Report
6. Methodology & Limitations

### 11.2 Global sidebar

Controls:

- exchange selector
- symbol selector
- timeframe selector
- date/time range
- refresh button
- auto-refresh toggle (60s)
- severity filter
- alert status filter

Data status display (always visible):

```
Data source:  Live  |  Sample fallback
Last fetched: 14:32 UTC
Candles loaded: 1,440
API status: OK  |  Unavailable — showing sample data
```

This display is not optional. It is part of the honesty contract with
the reviewer.

### 11.3 Overview page

- total alerts, alerts by severity, alerts by type
- latest alerts table
- top symbols by abnormal volume
- top symbols by price movement
- alert count by type chart
- severity distribution chart
- price/volume chart for selected symbol

### 11.4 Market Anomalies page

Three sections:

**Price anomalies table:** timestamp, symbol, return %, return z-score,
severity score, severity, alert ID

**Volume spikes table:** timestamp, symbol, current volume, rolling baseline,
volume z-score, volume multiplier, severity score, severity, alert ID

**Pump-and-dump candidates table:** symbol, pump start, peak time, reversal
time, pump return, reversal return, volume z-score, severity score, severity

Note: `severity_score` column is displayed in tables. This makes the scoring
transparent and is a deliberate design choice that signals analytical rigor.

### 11.5 Synthetic Surveillance Cases page

- wash trading candidate table
- spoofing/layering candidate table
- linked accounts table (not a hairball network graph)
- case status column with inline update controls

### 11.6 Alert Detail page

For selected alert:

- alert type, severity, severity score, status
- symbol, time window, trigger reason
- evidence table with metric/threshold/comparison/explanation columns
- chart around alert window
- recommended follow-up
- generated case note

Buttons:

- mark Under Review / Escalated / Closed
- download case report as Markdown

### 11.7 Daily Report page

Generated report includes:

- date/time, data source, symbols monitored
- alert summary by severity and type
- highest severity alerts
- top abnormal movements
- synthetic case summary
- limitations
- recommended follow-up

Export: copy Markdown / download `.md`

### 11.8 Methodology & Limitations page

Must include:

- public data limitations
- real vs synthetic data boundary
- ephemeral database constraint and what it means for the demo
- rule definitions and thresholds
- severity scoring methodology
- false positive risk
- not financial advice
- not actual market manipulation accusation

---

## 12. Ingestion Specification

### 12.1 `fetch_market_data.py`

```python
def fetch_ohlcv(
    exchange_id: str,
    symbols: list[str],
    timeframe: str,
    limit: int,
) -> pd.DataFrame: ...

def normalize_ohlcv(
    raw_rows: list[list],
    exchange: str,
    symbol: str,
    timeframe: str,
) -> pd.DataFrame: ...

def load_market_data(
    exchange_id: str,
    symbols: list[str],
    timeframe: str,
    limit: int,
    fallback_path: str,
) -> pd.DataFrame: ...
```

### 12.2 API error handling

Handle: rate limits, empty responses, unsupported symbols, exchange
unavailable, network timeout, malformed rows.

Behavior: show warning in UI, use sample fallback, do not crash, log error.

### 12.3 Data freshness

Display: latest candle timestamp, last fetch timestamp, exchange, timeframe,
whether data is live or sample fallback.

---

## 13. Detection Engine Specification

Each detection module must:

- accept DataFrame or database connection
- return standardized alert objects with dedup key
- create structured evidence
- be unit tested

```python
@dataclass
class Alert:
    alert_type: str
    severity: str
    severity_score: int
    exchange: str | None
    symbol: str | None
    start_time: str
    end_time: str
    evidence_summary: str
    recommended_follow_up: str
    dedup_key: str
    evidence: list[AlertEvidence]

@dataclass
class AlertEvidence:
    metric_name: str
    metric_value: float | None
    threshold_value: float | None
    comparison_operator: str | None
    explanation: str
```

---

## 14. Reporting Specification

### 14.1 Case report format

```
Case Report

Alert ID:
Alert Type:
Severity:
Severity Score:
Status:
Symbol:
Time Window:

Trigger Summary:
Evidence:
Recommended Follow-Up:
Limitations:
Generated At:
```

### 14.2 Example report

```
Alert Type: Pump-and-Dump Candidate
Severity: Medium
Severity Score: 55
Symbol: SOL/USDT
Time Window: 2026-05-23 10:00–11:00

Trigger Summary:
The symbol showed a rapid upward price movement with abnormal volume,
followed by a short-window reversal.

Evidence:
- Pump-window return: 6.4%
- Volume z-score: 3.8
- Reversal return: -3.2%
- Rolling baseline volume: 1.2M
- Observed volume: 4.9M

Recommended Follow-Up:
Review trade-level activity around the alert window. Compare movement
against broader market conditions. Escalate if similar patterns recur
across related accounts or symbols.

Limitations:
This alert is based on public market-level data and does not confirm
manipulation. Account-level identifiers are not available from public APIs.
```

---

## 15. Testing Specification

### 15.1 Unit tests per rule

**Price anomaly:** no alert for normal returns; alert for extreme return;
correct severity score; handles zero/NaN safely.

**Volume spike:** no alert for stable volume; alert for spike; score scales
with z-score; rolling baseline excludes current candle.

**Pump-and-dump:** no alert for pump without reversal; alert for all three
conditions; score accumulates correctly.

**Wash trading synthetic:** no alert for unlinked accounts; no alert if net
position ratio too high; alert for linked pair with low net ratio; score
increases with trade count and notional.

**Spoofing/layering synthetic:** no alert for normal cancellation rates;
alert for repeated large-cancel + opposite-trade pattern; `LARGE_ORDER_MULTIPLIER`
applied against account's own history, not population.

**Alert dedup:** see Section 10.3.

### 15.2 Integration tests

- database initializes and seeds correctly
- ingestion writes candles without duplicates
- detection pipeline inserts alerts with dedup keys
- second detection run does not duplicate existing alerts
- analyst status preserved across detection runs
- case report generates from alert
- dashboard loads sample data without crash

### 15.3 Quality gates

```bash
python -m pytest
python -m ruff check .
```

---

## 16. Engineering Standards

- no notebook-only implementation
- no giant `app.py` logic blob
- detection logic outside UI layer
- database logic outside UI layer
- clear function names, typed signatures
- small modules
- all thresholds in `config/thresholds.py`
- deterministic seeded synthetic data generation
- structured logging for fetch, insert, alert generation, fallback usage

---

## 17. README Specification

### Required sections

1. Project Overview
2. Why This Project Exists
3. Demo Link
4. Screenshots
5. Core Features
6. Architecture
7. Data Sources
8. Real vs Synthetic Data Boundary
9. Detection Rules
10. Severity Scoring
11. Database Schema
12. Deployment Constraints (SQLite / ephemeral filesystem)
13. How to Run Locally
14. Testing
15. Limitations
16. Future Work

### Required statements

**Real vs synthetic boundary:**
> Public exchange APIs expose market-level data but do not expose private
> account identifiers or full account-level order lifecycle data. This project
> uses real public market data for price/volume monitoring and synthetic
> account-level scenarios to demonstrate surveillance investigation workflows.
> The synthetic data is generated to approximate realistic account behavior,
> not random noise, but it does not represent real accounts or real transactions.

**Deployment constraint:**
> This application uses SQLite for local and demo deployments. Streamlit
> Community Cloud uses an ephemeral filesystem, so the database is rebuilt
> from committed sample data on each cold start. Live data fetched during a
> session is not persisted between sessions. For a production deployment,
> this layer would be replaced with a persistent database such as PostgreSQL.

---

## 18. Deployment Specification

Platform: Streamlit Community Cloud.

Requirements:

- public GitHub repo
- `requirements.txt`
- entrypoint: `app.py`
- sample data committed to `data/`
- no hardcoded secrets
- app runs when external API fetch fails

Checklist:

- app starts locally
- app starts from clean virtual environment
- API fallback tested and labeled in UI
- README has demo link and screenshots
- data freshness indicator visible on all pages
- limitations displayed prominently

---

## 19. Future Work (V2+)

1. WebSocket ingestion for true streaming updates.
2. PostgreSQL persistence for durable deployed storage.
3. Scheduled background ingestion.
4. Cross-exchange comparison.
5. Backtesting detection rules against known market events.
6. Analyst workflow persistence with authentication.
7. Slack/email alert notifications.
8. Real-time order book imbalance monitoring.
9. Network graph analysis for synthetic account clusters.
10. Configurable threshold tuning via UI.

---

## 20. Milestones

### Milestone 1: Skeleton
Repo created, structure in place, Streamlit boots, README stub exists.

### Milestone 2: Database + synthetic data
Schema works; synthetic population generated (all account types, behavioral
profiles, account links); all three scenarios injected; data queryable;
output matches expected volumes from Section 5.6.

### Milestone 3: Real market ingestion
CCXT fetch works locally; OHLCV normalized; rows inserted without duplicates;
fallback works and is labeled correctly in UI.

### Milestone 4: Detection engine
All five rules implemented; severity scoring unified in `severity.py`;
alert deduplication working; alerts + evidence inserted; second run
does not duplicate; analyst status preserved.

### Milestone 5: Dashboard
All pages functional; severity score column visible in tables; data source
indicator always displayed; filters work.

### Milestone 6: Reporting
Alert detail generates case report with severity score; daily report works;
Markdown download works; limitations included.

### Milestone 7: Testing and cleanup
All unit tests pass including dedup tests; integration tests pass; ruff passes;
no detection or UI logic mixed; thresholds centralized.

### Milestone 8: Deployment
Deployed link works; sample data visible on cold start; live data refresh
works and is labeled; README complete with demo link and screenshots;
resume bullets written.

---

## 21. Definition of Done

V1 is done when:

- public Streamlit demo link works
- public GitHub repo exists
- real public market data ingestion works with labeled fallback
- SQLite schema with dedup key on alerts
- five detection rules implemented with unified severity scoring
- alert dashboard with severity score column
- alert evidence view
- realistic synthetic account-level cases (three scenarios)
- case report generator with severity score field
- daily monitoring summary
- limitations and deployment constraints documented in UI and README
- all tests pass
- polished README with required statements

Not done if:

- severity scoring is duplicated across rule files and `severity.py`
- alert table fills with duplicates on repeated detection runs
- deployed app shows no data source indicator
- README omits the SQLite ephemeral constraint
- synthetic data is obviously random rather than behaviorally structured
- detection logic lives in UI code
- no case report exists
- no deployed link exists

---

## 22. Resume Bullets This Project Must Earn

- Built a deployed crypto market surveillance dashboard using Python, SQL,
  SQLite, and Streamlit to ingest public exchange market data, detect abnormal
  price/volume movements, and support alert triage workflows.

- Designed rule-based detection logic for volume spikes, price anomalies,
  pump-and-dump candidates, and synthetic account-level manipulation scenarios
  including wash trading and spoofing/layering patterns, with a unified
  severity scoring model applied consistently across all rule types.

- Generated realistic synthetic account-level datasets with behavioral
  profiles, account linkage structures, and embedded manipulation scenarios
  to model surveillance investigation workflows where public APIs provide
  no account-level visibility.

- Created structured case reports with severity scores, evidence summaries,
  time windows, recommended follow-up actions, and explicit data limitation
  disclosures to mirror market surveillance and risk operations workflows.

If the final build cannot support these bullets honestly, it is underbuilt.