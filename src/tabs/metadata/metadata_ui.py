"""Tab class for standardizing the currently 
    loaded HAR file and embedding experiment metadata into it."""

from datetime import datetime, time

import streamlit as st

from core.models import (
    ParsedEntry,
    embed_analysis,
    get_embedded_analysis,
    load_raw_har,
    serialize_har,
)
from tabs.metadata.metadata import StandardizeInputs, build_standardized_result
from tabs.naming.naming import (
    COOKIES_LABELS,
    INTERACT_LABELS,
    VISIT_LABELS,
    derive_metadata_from_entries,
)
from tabs.shared.selectors import select_by_label

class MetadataTab:
    """Class to render the metadata tab"""
    @property
    def title(self) -> str:
        """Name rendered on the Streamlit page tab selection bar."""
        return "Standardize & Tag"

    def render(self, entries: list[ParsedEntry]) -> None:
        """Isolated UI layout logic for standardizing and tagging the currently loaded HAR file."""
        st.subheader("Standardize & Tag Current HAR File")
        st.caption(
            "Modify and standardize metadata for the currently loaded HAR file. "
            "Domain and capture time are derived from the traffic itself, allowing "
            "you to confirm or override classification before generating an updated copy "
            "with embedded `log._analysis` metadata."
        )

        file_bytes = st.session_state.get("uploaded_file_bytes")

        if not file_bytes or not entries:
            st.warning("No active HAR file loaded. Please upload a file above.")
            return

        try:
            har_data = load_raw_har(file_bytes)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            st.error(f"Could not parse loaded file as JSON/HAR: {exc}")
            return

        try:
            derived = derive_metadata_from_entries(entries)
        except ValueError as exc:
            st.error(str(exc))
            return

        st.markdown("#### Detected from file contents")
        detect_col1, detect_col2 = st.columns(2)
        with detect_col1:
            st.metric("Primary domain", derived.domain)
        with detect_col2:
            captured_label = (
                derived.captured_at.strftime("%Y-%m-%d %H:%M")
                if derived.captured_at is not None
                else "Unknown"
            )
            st.metric("Earliest capture time", captured_label)

        if derived.other_domains:
            st.warning(
                "Multiple domains appear in this capture -- also saw: "
                f"{', '.join(derived.other_domains)}. Confirm the primary "
                "domain below before continuing."
            )

        if derived.captured_at is None:
            st.error(
                "Could not parse a capture timestamp from any entry's "
                "startedDateTime. Enter one manually below."
            )

        existing_analysis = get_embedded_analysis(har_data)
        overwrite_confirmed = True
        if existing_analysis is not None:
            st.warning("This file already has embedded experiment metadata:")
            st.json(existing_analysis.to_dict())
            overwrite_confirmed = st.checkbox(
                "Overwrite the existing metadata with the values below.",
                value=True,
                key="meta_overwrite_confirm",
            )

        st.markdown("#### Confirm classification")
        col1, col2 = st.columns(2)

        default_domain = (
            existing_analysis.domain
            if existing_analysis and getattr(existing_analysis, "domain", None)
            else derived.domain
        )

        with col1:
            domain = st.text_input("Domain", value=default_domain, key="meta_domain")
            interact = select_by_label("Interaction type", INTERACT_LABELS, key="meta_interact")
            cookies = select_by_label("Cookie handling", COOKIES_LABELS, key="meta_cookies")
        with col2:
            visit = select_by_label("Visit type", VISIT_LABELS, key="meta_visit")
            extra = st.text_input(
                "Extra context (optional)", max_chars=32, key="meta_extra"
            )
            default_dt = derived.captured_at or datetime.now()
            capture_date = st.date_input("Capture date", value=default_dt.date(), key="meta_date")
            capture_hour = st.number_input(
                "Capture hour (24h)",
                min_value=0,
                max_value=23,
                value=default_dt.hour,
                key="meta_hour",
            )

        st.markdown("#### Experiment notes")
        st.caption("Written into log._analysis inside the file itself, not just the filename.")

        default_desc = existing_analysis.description if existing_analysis else ""
        default_email = existing_analysis.email_used if existing_analysis else ""
        default_notes = existing_analysis.notes if existing_analysis else ""

        description = st.text_area("Description", value=default_desc, key="meta_description")
        email_used = st.text_input("Email used", value=default_email, key="meta_email")
        notes = st.text_area("Notes", value=default_notes, key="meta_notes")

        if not domain.strip():
            st.info("Enter a domain to generate the filename.")
            return

        if existing_analysis is not None and not overwrite_confirmed:
            st.info("Confirm overwrite above to generate an updated file.")
            return

        captured_at = datetime.combine(capture_date, time(hour=int(capture_hour)))

        inputs = StandardizeInputs(
            domain=domain,
            interact=interact,
            cookies=cookies,
            visit=visit,
            extra=extra,
            captured_at=captured_at,
            description=description,
            email_used=email_used,
            notes=notes,
        )

        try:
            filename, analysis = build_standardized_result(inputs)
        except ValueError as exc:
            st.error(str(exc))
            return

        updated_har = embed_analysis(har_data, analysis)
        output_bytes = serialize_har(updated_har)

        st.markdown("#### Result")
        st.code(filename, language="text")
        st.download_button(
            "Download standardized .har",
            data=output_bytes,
            file_name=filename,
            mime="application/json",
            key="meta_download",
        )
