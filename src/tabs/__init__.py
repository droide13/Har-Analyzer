"""Package initialization to expose tab components cleanly."""

from .identifiers.identifiers import IdentifiersTab
from .cookies import CookiesTab
from .history.history import HistoryTab
from .overview import OverviewTab
from .query_params import QueryParamsTab
from .networklog import NetworkLogTab

__all__ = ["NetworkLogTab", "OverviewTab", "CookiesTab",
           "QueryParamsTab","IdentifiersTab", "HistoryTab"]
