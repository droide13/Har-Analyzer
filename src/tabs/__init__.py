"""Package initialization to expose tab components cleanly."""

from tabs.identifiers import IdentifiersTab

from .cookies import CookiesTab
from .overview import OverviewTab
from .protocols import Tab
from .requests import RequestsTab

__all__ = ["Tab", "RequestsTab", "OverviewTab", "CookiesTab", "IdentifiersTab"]
