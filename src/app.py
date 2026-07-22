"""Streamlit initialization orchestrator parsing raw streams."""

import streamlit as st

from core.models import get_embedded_analysis, load_parsed_entries, load_raw_har
from core.protocols import Tab
from tabs import (
    CookiesTab,
    IdentifiersTab,
    MetadataTab,
    NetworkLogTab,
    OverviewTab,
    QueryParamsTab,
)
from tabs.history import HistoryTab
from tabs.naming.naming import get_attrs_from_har_name
from tabs.naming.naming_ui import render_naming_tool

st.set_page_config(
    page_title="HAR Visualizer",
    page_icon="assets/har_analyzer.png",
    layout="wide",
)

_MODE_ANALYZE = "Analyze HAR"
_MODE_GENERATE = "Generate Filename"


def display_filename_metadata(filename: str) -> None:
    """Renders structured metadata if the filename follows standard schema."""
    attrs = get_attrs_from_har_name(filename)
    if not attrs:
        return

    # Render layout using the decoupled properties dictionary
    with st.container(border=True):
        st.markdown(f"### Session Metadata: {attrs['domain']}")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"Interaction Flow\n\n{attrs['interaction']}")
        with col2:
            st.markdown(f"Cookie Action\n\n{attrs['cookies']}")
        with col3:
            st.markdown(f"Visit Context\n\n{attrs['visit']}")
        with col4:
            st.markdown(f"Recorded Time\n\n{attrs['timestamp']}")
        with col5:
            st.markdown(f"Extra:\n\n{attrs['extra'] if attrs['extra'] != '000' else 'N/a'}")


def render_analyzer() -> None:
    """Upload-driven HAR analysis flow."""
    uploaded_file = st.file_uploader(
        "Upload your HTTP Archive document below (.har)", type=["har", "json"]
    )
    if uploaded_file is None:
        st.info("Please upload a .har export to initialize.")
        return

    try:
        file_bytes = uploaded_file.getvalue()

        # Store uploaded file state for tab access (e.g., MetadataTab)
        st.session_state["uploaded_file_bytes"] = file_bytes
        st.session_state["uploaded_file_name"] = uploaded_file.name

        # Validate filename convention and embedded experiment metadata
        attrs = get_attrs_from_har_name(uploaded_file.name)
        has_embedded_analysis = False
        try:
            har_data = load_raw_har(file_bytes)
            has_embedded_analysis = get_embedded_analysis(har_data) is not None
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        is_metadata_valid = bool(attrs) and has_embedded_analysis

        if is_metadata_valid:
            display_filename_metadata(uploaded_file.name)
        else:
            st.warning(
                f"⚠️ **Metadata Notice:** `{uploaded_file.name}` does not follow the "
                "standardized naming pattern or lacks embedded `log._analysis` metadata.\n\n"
                "Please use the **Standardize & Tag** tab below" 
                "to confirm classification and export a standardized HAR file."
            )

        st.divider()
        entries = load_parsed_entries(file_bytes)

        # Tab configuration: prioritize MetadataTab if metadata/naming is invalid
        if not is_metadata_valid:
            tabs_to_render: list[Tab] = [
                MetadataTab(),
                NetworkLogTab(),
                OverviewTab(),
                CookiesTab(),
                QueryParamsTab(),
                IdentifiersTab(),
                HistoryTab(),
            ]
        else:
            tabs_to_render: list[Tab] = [
                NetworkLogTab(),
                OverviewTab(),
                CookiesTab(),
                QueryParamsTab(),
                IdentifiersTab(),
                HistoryTab(),
                MetadataTab(),
            ]

        tab_layouts = st.tabs([t.title for t in tabs_to_render])
        for layout, tab_module in zip(tab_layouts, tabs_to_render):
            with layout:
                tab_module.render(entries)

    except Exception as exc:  # pylint: disable=broad-except
        st.error(f"Execution Error: {exc}")
        st.exception(exc)


def main() -> None:
    """Main function to render the application divided into analyzer and naming tools."""
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
