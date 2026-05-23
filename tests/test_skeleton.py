"""Skeleton milestone smoke tests."""

from __future__ import annotations

from pathlib import Path


def test_streamlit_entrypoint_exists() -> None:
    """Confirm the Community Cloud entrypoint is present."""
    assert Path("app.py").is_file()
