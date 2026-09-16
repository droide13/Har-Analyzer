"""Core analysis orchestrator for processing HAR files and rendering UI tabs."""

from datetime import datetime
from typing import Any

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
    DisseminationTab
)

from tabs.naming.naming import get_attrs_from_har_name


def display_filename_metadata(filename: str, capture_date_str: str) -> None:
    """Renders structured metadata cards"""
    attrs = get_attrs_from_har_name(filename) or {}
    domain = attrs.get("domain", "Unknown Domain")

    with st.container(border=True):
        st.markdown(f"### Session Metadata: `{domain}`")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"**Interaction Flow**\n\n{attrs.get('interaction', 'N/A')}")
        with col2:
            st.markdown(f"**Cookie Action**\n\n{attrs.get('cookies', 'N/A')}")
        with col3:
            st.markdown(f"**Visit Context**\n\n{attrs.get('visit', 'N/A')}")
        with col4:
            st.markdown(f"**Traffic Capture Date**\n\n{capture_date_str}")
        with col5:
            extra_val = attrs.get("extra", "000")
            st.markdown(f"**Extra Context**\n\n{extra_val if extra_val != '000' else 'N/A'}")


def _extract_analysis_info(file_bytes: bytes) -> tuple[bool, str]:
    """Extract embedded metadata presence and formatted analysis date."""
    try:
        har_data = load_raw_har(file_bytes)
        existing_analysis = get_embedded_analysis(har_data)
        if existing_analysis is None:
            return False, "Not Embedded"

        captured_at: Any = getattr(existing_analysis, "captured_at", None)
        # Try parsing string
        if isinstance(captured_at, str):
            try:
                captured_at = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            except ValueError:
                return True, captured_at  # unparseable, show as-is

        if isinstance(captured_at, datetime):
            return True, captured_at.astimezone().strftime("%Y-%m-%d %H:%M")
        if captured_at is not None:
            return True, str(captured_at)

        return True, "Present"
    except Exception:  # pylint: disable=broad-exception-caught
        return False, "Not Embedded"


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

        # Store uploaded file state in session for tab access (e.g. MetadataTab)
        st.session_state["uploaded_file_bytes"] = file_bytes
        st.session_state["uploaded_file_name"] = uploaded_file.name

        entries = load_parsed_entries(file_bytes)

        # Capture date derived from embedded log._analysis metadata
        has_embedded_analysis, analysis_date_str = _extract_analysis_info(file_bytes)

        # Validate filename convention and embedded experiment metadata
        attrs = get_attrs_from_har_name(uploaded_file.name)
        is_file_format_valid = True
        error_s = ""

        # Check independently naming and metadata
        if not bool(attrs):
            is_file_format_valid = False
            error_s = error_s + "- The file does not follow the naming pattern\n"

        if not has_embedded_analysis:
            is_file_format_valid = False
            error_s = error_s + "- The file does not contain the analysis metadata\n"

        if is_file_format_valid:
            display_filename_metadata(uploaded_file.name, analysis_date_str)

        else:
            st.warning(
                f"⚠️ **Metadata Notice:** `{uploaded_file.name}` contains format errors:\n"
                + error_s + "\n" +
                "Please use the **Metadata** tab below to confirm "
                "classification and export a standardized HAR file."
            )


        st.divider()

        # Tab configuration: prioritize MetadataTab if metadata/naming is invalid
        if not is_file_format_valid:
            tabs_to_render: list[Tab] = [
                MetadataTab(),
                NetworkLogTab(),
                OverviewTab(),
                CookiesTab(),
                QueryParamsTab(),
                IdentifiersTab(),
                DisseminationTab(),
            ]
        else:
            tabs_to_render: list[Tab] = [
                NetworkLogTab(),
                OverviewTab(),
                CookiesTab(),
                QueryParamsTab(),
                IdentifiersTab(),
                DisseminationTab(),
                MetadataTab(),
            ]

        tab_layouts = st.tabs([t.title for t in tabs_to_render])
        for layout, tab_module in zip(tab_layouts, tabs_to_render):
            with layout:
                tab_module.render(entries)

    except Exception as exc:  # pylint: disable=broad-except
        st.error(f"Execution Error: {exc}")
        st.exception(exc)
