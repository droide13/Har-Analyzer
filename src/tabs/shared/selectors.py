"""Streamlit label-based selectbox helpers, shared by more than one tab.

Kept out of ``core/models.py`` (pure data, no Streamlit) and out of
``tabs/naming/naming.py`` (pure filename logic, no Streamlit), and out of
any single tab's ``*_ui.py`` module, so it can be imported by every tab that
needs the same label -> internal-key dropdown behavior without duplicating it.
"""

import streamlit as st


def select_by_label(label: str, options: dict[str, str], *, key: str) -> str:
    """Render a selectbox showing human-friendly labels, return the internal key.

    ``options`` maps internal key -> display label, e.g. ``{"login": "Login"}``.
    The widget shows the labels; the function returns whichever key matches
    the label the user picked.
    """
    choice = st.selectbox(label, list(options.values()), key=key)
    return next(k for k, v in options.items() if v == choice)
