"""Package initialization to expose tab components cleanly."""

from .cookies import CookiesTab
from .history import HistoryTab
from .identifiers.identifiers import IdentifiersTab
from .networklog import NetworkLogTab
from .overview import OverviewTab
from .query_params import QueryParamsTab
from .metadata.metadata_ui import MetadataTab

__all__ = [
    "NetworkLogTab",
    "OverviewTab",
    "CookiesTab",
    "QueryParamsTab",
    "IdentifiersTab",
    "HistoryTab",
    "MetadataTab"
]
