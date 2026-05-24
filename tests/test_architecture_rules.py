"""Architecture guardrails from the build specification."""

from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_FILES = sorted((PROJECT_ROOT / "src" / "ui").glob("*.py"))
DETECTION_RULE_NAMES = {
    "detect_price_anomalies",
    "detect_volume_spikes",
    "detect_pump_dump_candidates",
    "detect_wash_trading",
    "detect_spoofing_layering",
    "severity_from_score",
    "price_anomaly_score",
    "volume_spike_score",
    "pump_dump_score",
    "wash_trading_score",
    "spoofing_layering_score",
}
THRESHOLD_CONSTANT_NAMES = {
    "RETURN_Z_THRESHOLD",
    "VOLUME_Z_THRESHOLD",
    "PUMP_RETURN_THRESHOLD",
    "REVERSAL_THRESHOLD",
    "MIN_PAIR_TRADES",
    "LARGE_ORDER_MULTIPLIER",
    "MIN_REPEATED_EVENTS",
}


def test_ui_does_not_import_detection_or_severity_modules() -> None:
    """Detection and severity logic must stay out of src/ui."""
    violations = []
    for path in UI_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                violations.extend(
                    f"{path}: import {alias.name}"
                    for alias in node.names
                    if alias.name.startswith("src.detection")
                )
            elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("src.detection"):
                violations.append(f"{path}: from {node.module} import ...")

    assert violations == []


def test_ui_does_not_contain_rule_or_threshold_logic() -> None:
    """UI files should not reference detection rules or central thresholds."""
    violations = []
    forbidden_names = DETECTION_RULE_NAMES | THRESHOLD_CONSTANT_NAMES
    for path in UI_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden_names:
                violations.append(f"{path}: {node.id}")

    assert violations == []
