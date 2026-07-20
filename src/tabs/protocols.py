"""Interface boundaries that guarantee tab interchangeability."""

from typing import Protocol

from models import ParsedEntry


class Tab(Protocol):
    @property
    def title(self) -> str:
        """Name rendered on the Streamlit page tab selection bar."""
        ...

    def render(self, entries: list[ParsedEntry]) -> None:
        """Isolated UI layout logic."""
        ...
