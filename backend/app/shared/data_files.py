"""Where this app's own static reference data lives -- one place trackers.py
and known_ids.py both resolve it from, instead of each recomputing the same
relative path."""

from pathlib import Path

APP_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
