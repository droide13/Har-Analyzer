"""Package initialization to expose tab components cleanly."""

from .cookies import CookiesTab
from .dissemination.dissemination_ui import DisseminationTab
from .identifiers.identifiers import IdentifiersTab
from .metadata.metadata_ui import MetadataTab
from .networklog import NetworkLogTab
from .overview.overview_ui import OverviewTab
from .query_params import QueryParamsTab

__all__ = [
    "NetworkLogTab",
    "OverviewTab",
    "CookiesTab",
    "QueryParamsTab",
    "IdentifiersTab",
    "DisseminationTab",
    "MetadataTab",
]
