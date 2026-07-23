"""Grabs the app version out of pyproject.toml instead of hardcoding it.

We use this for log._analysis.tool_version so the version on every file you
standardize always matches what's actually running -- bump pyproject.toml
once and everything tagged after that just picks it up.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, cast

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

# This file lives at <repo root>/src/core/app_version.py, so three parents
# up gets us back to the repo root. Update this if the file ever moves.
_PYPROJECT_PATH: Path = Path(__file__).resolve().parents[2] / "pyproject.toml"

_FALLBACK_VERSION: str = "0.0.0-unknown"


@lru_cache(maxsize=1)
def get_app_version() -> str:
    """Read the version straight out of pyproject.toml, cached so we only do it once."""
    try:
        with _PYPROJECT_PATH.open("rb") as f:
            data = cast(dict[str, Any], tomllib.load(f))
    except (OSError, tomllib.TOMLDecodeError):
        return _FALLBACK_VERSION

    project_table = cast(dict[str, Any], data.get("project", {}) or {})
    version = project_table.get("version")
    if isinstance(version, str) and version:
        return version

    return _FALLBACK_VERSION