"""Streamlit initialization orchestrator parsing raw streams."""

import streamlit as st
from models import load_parsed_entries
from tabs import Tab, RequestsTab, OverviewTab, CookiesTab, IdentifiersTab

def main() -> None:
    st.title("HAR Visualizer")
    
    uploaded_file = st.file_uploader(
        "Upload your HTTP Archive document below (.har)", 
        type=["har", "json"]
    )

    if uploaded_file is None:
        st.info("Please upload a `.har` export to initialize.")
        return

    try:
        entries = load_parsed_entries(uploaded_file.getvalue())
        
        with st.sidebar:
            st.success(f"File loaded: {uploaded_file.name}")
            if st.button("Reset Session"):
                st.rerun()

        # Tabs config - Simply add new tab classes directly to this list!
        tabs_to_render: list[Tab] = [
            RequestsTab(),
            OverviewTab(),
            CookiesTab(),
            IdentifiersTab()
        ]

        # Layout allocation using standard Streamlit Tab Components
        tab_layouts = st.tabs([t.title for t in tabs_to_render])
        for layout, tab_module in zip(tab_layouts, tabs_to_render):
            with layout:
                tab_module.render(entries)

    except Exception as exc:
        st.error(f"Execution Error: {exc}")
        st.exception(exc)

if __name__ == "__main__":
    main()