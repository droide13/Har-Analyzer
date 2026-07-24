"""Streamlit initialization orchestrator."""

import streamlit as st

from core.analyzer import render_analyzer

## Eliminate har naming mode, keep code for possible fallback
# from tabs.naming.naming_ui import render_naming_tool

st.set_page_config(
    page_title="HAR Visualizer",
    page_icon="assets/har_analyzer.png",
    layout="wide",
)

_MODE_ANALYZE = "Analyze HAR"
_MODE_GENERATE = "Generate Filename"


def main() -> None:
    """Main function to render the application divided into analyzer and naming tools."""
    st.title("HAR Analyzer")
    ## Eliminate har naming mode, keep code for possible fallback
    # mode = st.segmented_control(
    #     "Mode",
    #     options=[_MODE_ANALYZE, _MODE_GENERATE],
    #     default=_MODE_ANALYZE,
    #     label_visibility="collapsed",
    #     key="app_mode",
    # )
    # st.divider()

    # if mode == _MODE_GENERATE:
    #     render_naming_tool()
    # else:
    #     render_analyzer()
    render_analyzer()


if __name__ == "__main__":
    main()
