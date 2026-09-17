"""Interface boundaries that guarantee tab interchangeability."""

from typing import Protocol

from core.models import ParsedEntry


class Tab(Protocol):
    """Interface every tab implements: a title and a render method."""

    @property
    def title(self) -> str:
        """Name rendered on the Streamlit page tab selection bar."""

    def render(self, entries: list[ParsedEntry]) -> None:
        """Isolated UI layout logic."""
