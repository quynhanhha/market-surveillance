PRAGMA foreign_keys = ON;

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

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    account_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    risk_tier TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    avg_daily_volume REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS account_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id_a TEXT NOT NULL,
    account_id_b TEXT NOT NULL,
    link_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    FOREIGN KEY(account_id_a) REFERENCES accounts(account_id),
    FOREIGN KEY(account_id_b) REFERENCES accounts(account_id)
);

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
