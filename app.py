"""Streamlit entrypoint for the surveillance dashboard skeleton."""

from __future__ import annotations

import streamlit as st


APP_TITLE = "Crypto Market Surveillance Analytics"


def main() -> None:
    """Render the Milestone 1 placeholder app."""
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    st.title(APP_TITLE)
    st.caption("Milestone 1: project skeleton")
    st.info("Data source: Sample data - skeleton placeholder")


if __name__ == "__main__":
    main()
