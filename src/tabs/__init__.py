"""Package initialization to expose tab components cleanly."""

from .protocols import Tab
from .requests import RequestsTab
from .overview import OverviewTab
from .cookies import CookiesTab

__all__ = ["Tab", "RequestsTab", "OverviewTab", "CookiesTab"]