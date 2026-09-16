"""The Standardize & Tag tab: lets you review the domain/time we detected from
the loaded HAR file, fill in a few classification fields, and download a copy
with that metadata embedded in log._analysis.

Writing the metadata into the file is an explicit action (the "Generate
standardized file" button), not a side effect of rendering. The resulting
bytes/filename are frozen in ``st.session_state`` and that snapshot is what
the download button serves - so the download can never disagree with what's
on screen, regardless of reruns, ctrl-click, or anything else that re-renders
the page after generation.
"""

from datetime import datetime, time
from typing import Any, cast

import streamlit as st

from core.models import (
    HarAnalysis,
    ParsedEntry,
    embed_analysis,
    get_embedded_analysis,
    load_raw_har,
    serialize_har,
)
from tabs.metadata.metadata import (
    StandardizeInputs,
    analysis_table_rows,
    build_signature,
    build_standardized_result,
    collect_domain_options,
    is_custom_domain_choice,
)
from tabs.naming.naming import (
    COOKIES_LABELS,
    INTERACT_LABELS,
    VISIT_LABELS,
    derive_metadata_from_entries,
)
from tabs.shared.selectors import select_by_label

_BYTES_KEY = "meta_generated_bytes"
_FILENAME_KEY = "meta_generated_filename"
_SIGNATURE_KEY = "meta_generated_signature"


class MetadataTab:
    """The Standardize & Tag tab."""

    @property
    def title(self) -> str:
        """What shows up on the tab bar."""
        return "Metadata"

    def render(self, entries: list[ParsedEntry]) -> None:
        """Draws the tab: detected info up top, form in the middle, download at the bottom."""
        st.subheader("Standardize & Tag Current HAR File")
        st.caption(
            "Modify and standardize metadata for the currently loaded HAR file. "
            "Domain and capture time are derived from the traffic itself, allowing "
            "you to confirm or override classification before generating an updated "
            "copy with embedded log._analysis metadata."
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

        domain_options, first_request_domain = collect_domain_options(
            entries, derived.domain, frozenset(derived.other_domains)
        )
        existing_analysis = get_embedded_analysis(har_data)

        self._render_detected_section(
            first_request_domain, derived.captured_at, len(domain_options)
        )

        overwrite_confirmed = True
        if existing_analysis is not None:
            st.markdown("#### Current metadata")
            st.table(analysis_table_rows(existing_analysis))
            overwrite_confirmed = st.checkbox(
                "I want to overwrite this with new values below.",
                value=False,
                key="meta_overwrite_confirm",
            )

        inputs = self._render_form(
            domain_options, derived.captured_at, existing_analysis, overwrite_confirmed
        )
        if inputs is None:
            return  # folded: nothing more to do until the user opts in above

        if not inputs.domain.strip():
            st.info("Enter or select a domain to generate the filename.")
            return

        self._render_generate_and_download(har_data, file_bytes, inputs)

    @staticmethod
    def _render_detected_section(
        first_request_domain: str, captured_at: datetime | None, option_count: int
    ) -> None:
        st.markdown("#### Detected from file contents")
        detect_col1, detect_col2 = st.columns(2)
        with detect_col1:
            st.metric("Primary domain (first request)", first_request_domain)
        with detect_col2:
            # Show captured time with correct timezone, if no time found show unknown
            if captured_at:
                captured_label = captured_at.astimezone().strftime("%Y-%m-%d %H:%M")
            else:
                captured_label = "Unknown"
            st.metric("Capture time", captured_label)

        if option_count > 2:  # more than one real domain, excl. "Custom domain..."
            st.info(
                f"First request domain is `{first_request_domain}`. "
                f"Found {option_count - 1} distinct domains in total. "
                "Use the dropdown below to select another domain if needed."
            )

        if captured_at is None:
            st.error(
                "Could not parse a capture timestamp from any entry's "
                "startedDateTime. Enter one manually below."
            )

    @staticmethod
    def _render_form(
        domain_options: list[str],
        derived_captured_at: datetime | None,
        existing_analysis: HarAnalysis | None,
        overwrite_confirmed: bool,
    ) -> StandardizeInputs | None:
        """Renders the classification form and returns the collected inputs.

        When there's already metadata on the file, the form is tucked into a
        collapsed expander so the tab doesn't hit you with a full re-fill form
        just to look at a file you've already tagged. It only opens once you
        check "overwrite" above, or you can expand it manually to peek.
        Returns ``None`` if the form never rendered (folded + not opted in).
        """
        has_existing = existing_analysis is not None
        if not has_existing:
            return MetadataTab._render_form_fields(
                domain_options, derived_captured_at, existing_analysis
            )

        with st.expander("Edit metadata", expanded=overwrite_confirmed):
            if not overwrite_confirmed:
                st.caption('Check "I want to overwrite this" above to edit and regenerate.')
            return MetadataTab._render_form_fields(
                domain_options, derived_captured_at, existing_analysis
            )

    @staticmethod
    def _render_form_fields(
        domain_options: list[str],
        derived_captured_at: datetime | None,
        existing_analysis: HarAnalysis | None,
    ) -> StandardizeInputs:
        st.markdown("#### Confirm classification")
        col1, col2 = st.columns(2)

        with col1:
            selected_domain_opt = st.selectbox(
                "Domain",
                options=domain_options,
                index=0,
                key="meta_domain_select",
                help="Defaults to the domain of the first request in the HAR file.",
            )
            domain = (
                st.text_input("Custom Domain", value="", key="meta_domain_custom")
                if is_custom_domain_choice(selected_domain_opt)
                else selected_domain_opt
            )
            interact = select_by_label("Interaction type", INTERACT_LABELS, key="meta_interact")
            cookies = select_by_label("Cookie handling", COOKIES_LABELS, key="meta_cookies")

        with col2:
            visit = select_by_label("Visit type", VISIT_LABELS, key="meta_visit")
            extra = st.text_input("Extra context (optional)", key="meta_extra")

            # If there is a date derived from the har file keep it, else let user choose
            if derived_captured_at:
                captured_at = derived_captured_at
            else:
                capture_date = st.datetime_input("Capture date", key="meta_date")
                captured_at = capture_date

        st.markdown("#### Experiment notes")
        st.caption("Written into log._analysis inside the file itself, not just the filename.")

        default_desc = existing_analysis.description if existing_analysis else ""
        default_email = existing_analysis.email_used if existing_analysis else ""
        default_notes = existing_analysis.notes if existing_analysis else ""

        description = st.text_area("Description", value=default_desc, key="meta_description")
        email_used = st.text_input("Email used", value=default_email, key="meta_email")
        notes = st.text_area("Notes", value=default_notes, key="meta_notes")


        return StandardizeInputs(
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

    @staticmethod
    def _render_generate_and_download(
        har_data: dict[str, Any], file_bytes: bytes, inputs: StandardizeInputs
    ) -> None:
        current_signature = build_signature(file_bytes, inputs)

        st.markdown("#### Standardized Output")
        if st.button("Generate standardized file", key="meta_generate_btn", type="primary"):
            try:
                filename, analysis = build_standardized_result(inputs)
            except ValueError as exc:
                st.error(str(exc))
                return
            updated_har = embed_analysis(har_data, analysis)
            st.session_state[_BYTES_KEY] = serialize_har(updated_har)
            st.session_state[_FILENAME_KEY] = filename
            st.session_state[_SIGNATURE_KEY] = current_signature

        generated_bytes = cast(bytes | None, st.session_state.get(_BYTES_KEY))
        generated_filename = cast(str | None, st.session_state.get(_FILENAME_KEY))

        if generated_bytes is None or generated_filename is None:
            st.info('Fill in the fields above and click "Generate standardized file".')
            return

        if st.session_state.get(_SIGNATURE_KEY) != current_signature:
            st.warning(
                "Form values changed since this file was generated. "
                'Press "Generate standardized file" again to update the download.'
            )

        st.code(generated_filename, language="text")
        st.download_button(
            "Download Standardized .har",
            data=generated_bytes,
            file_name=generated_filename,
            mime="application/json",
            key="meta_download",
        )
        st.caption(
            "Note on browser save location: web browsers determine whether files "
            "download directly or open a save dialog. To be prompted for a folder "
            'path on every download, enable "Ask where to save each file before '
            "downloading\" in your browser's settings (for example, Chrome Settings "
            "> Downloads)."
        )
