"""Streamlit initialization orchestrator parsing raw streams."""

import streamlit as st

from models import load_parsed_entries
from naming_ui import render_naming_tool
from tabs import CookiesTab, IdentifiersTab, OverviewTab, RequestsTab, Tab

st.set_page_config(
    page_title="HAR Visualizer",
    page_icon="assets/har_analyzer.png",
    layout="wide",
)

_MODE_ANALYZE = "Analyze HAR"
_MODE_GENERATE = "Generate Filename"


def render_analyzer() -> None:
    """Upload-driven HAR analysis flow."""
    uploaded_file = st.file_uploader(
        "Upload your HTTP Archive document below (.har)", type=["har", "json"]
    )

    if uploaded_file is None:
        st.info("Please upload a `.har` export to initialize.")
        return

    try:
        entries = load_parsed_entries(uploaded_file.getvalue())

        # Tabs config - Simply add new tab classes directly to this list!
        tabs_to_render: list[Tab] = [
            RequestsTab(),
            OverviewTab(),
            CookiesTab(),
            IdentifiersTab(),
        ]

        tab_layouts = st.tabs([t.title for t in tabs_to_render])
        for layout, tab_module in zip(tab_layouts, tabs_to_render):
            with layout:
                tab_module.render(entries)

    except Exception as exc:
        st.error(f"Execution Error: {exc}")
        st.exception(exc)


def main() -> None:
    st.title("HAR Analyzer")

    mode = st.segmented_control(
        "Mode",
        options=[_MODE_ANALYZE, _MODE_GENERATE],
        default=_MODE_ANALYZE,
        label_visibility="collapsed",
        key="app_mode",
    )
    st.divider()

    if mode == _MODE_GENERATE:
        render_naming_tool()
    else:
        render_analyzer()


if __name__ == "__main__":
    main()