# Crypto Market Surveillance — Agent Instructions

## Read first
Full build spec: docs/BUILD_SPEC.md
Starting from scratch

## Architecture rules
- Detection logic lives only in src/detection/ — never in src/ui/
- Severity scoring lives only in src/detection/severity.py — no per-rule severity logic elsewhere
- Thresholds live only in src/config/thresholds.py — no magic numbers in other files
- Database logic lives only in src/storage/ — never in app.py or ui files

## Non-negotiables
- All alert inserts use ON CONFLICT(dedup_key) DO NOTHING
- dedup_key = sha256 of "alert_type|symbol|start_time|end_time|account_id"
- start_time/end_time use candle timestamp, never fetched_at or datetime.utcnow()
- Synthetic data generation is seeded (seed=42) and deterministic

## Done means
- python -m pytest passes
- python -m ruff check . passes
- No detection or severity logic in UI files