"""Streamlit initialization orchestrator."""

import streamlit as st

from core.analyzer import render_analyzer

st.set_page_config(
    page_title="HAR Visualizer",
    page_icon="assets/har_analyzer.png",
    layout="wide",
)


def main() -> None:
    """Main function to render the application."""
    st.title("HAR Analyzer")
    render_analyzer()


if __name__ == "__main__":
    main()
