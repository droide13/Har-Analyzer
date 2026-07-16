"""Streamlit UI for generating standardized .har test filenames."""

import streamlit as st

from naming import get_har_filename

# Human-readable labels shown in the UI, mapped back to internal keys.
_INTERACT_LABELS: dict[str, str] = {
    "load": "Load page",
    "navigate": "Navigate",
    "enter_email": "Enter email",
    "sign_up": "Sign up",
    "login": "Login",
}

_COOKIES_LABELS: dict[str, str] = {
    "accept": "Accept",
    "deny": "Deny",
    "ignore": "Ignore",
}

_VISIT_LABELS: dict[str, str] = {
    "first": "First visit (fresh state)",
    "second": "Second visit (reuse existing cookies/state)",
    "delete": "Delete cookies & reload (regenerate from scratch)",
}


def _select_by_label(label: str, options: dict[str, str], key: str) -> str:
    """Render a selectbox showing human-friendly labels, return the internal key."""
    choice = st.selectbox(label, list(options.values()), key=key)
    return next(k for k, v in options.items() if v == choice)


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
        interact = _select_by_label("Interaction type", _INTERACT_LABELS, key="name_interact")
        cookies = _select_by_label("Cookie handling", _COOKIES_LABELS, key="name_cookies")
    with col2:
        visit = _select_by_label("Visit type", _VISIT_LABELS, key="name_visit")
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