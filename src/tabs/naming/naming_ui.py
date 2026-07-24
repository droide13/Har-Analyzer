"""Streamlit rendering for the HAR filename generator."""

import streamlit as st

from tabs.naming.naming import (
    COOKIES_LABELS,
    INTERACT_LABELS,
    VISIT_LABELS,
    get_har_filename,
)
from tabs.shared.selectors import select_by_label


def render_naming_tool() -> None:
    """Render the standalone HAR filename generator, independent of any upload."""
    st.subheader("HAR Test Filename Generator")
    st.caption(
        "Build a standardized filename for a test scenario before capturing "
        "the corresponding .har file."
    )

    col1, col2 = st.columns(2)
    with col1:
        domain = st.text_input("Domain under test", placeholder="domain.com", key="name_domain")
        interact = select_by_label("Interaction type", INTERACT_LABELS, key="name_interact")
        cookies = select_by_label("Cookie handling", COOKIES_LABELS, key="name_cookies")
    with col2:
        visit = select_by_label("Visit type", VISIT_LABELS, key="name_visit")
        extra = st.text_input(
            "Extra context (optional)",
            placeholder="e.g. staging",
            max_chars=32,
            key="name_extra",
        )
    st.caption("Only the first 3 letters of the extra text are used; blank defaults to '000'.")

    if not domain.strip():
        st.info("Enter a domain to generate the filename.")
        return

    try:
        filename = get_har_filename(
            domain=domain, interact=interact, cookies=cookies, visit=visit, extra=extra
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    st.markdown("#### Generated filename")
    st.code(filename, language="text")
    st.caption("Copy this filename, then save the recorded .har capture under it.")
