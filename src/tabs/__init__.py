"""Package initialization to expose tab components cleanly."""

from tabs.identifiers import IdentifiersTab

from .cookies import CookiesTab
from .history import HistoryTab
from .overview import OverviewTab
from .query_params import QueryParamsTab
from .protocols import Tab
from .requests import RequestsTab

__all__ = ["Tab", "RequestsTab", "OverviewTab", "CookiesTab",
           "QueryParamsTab","IdentifiersTab", "HistoryTab"]
