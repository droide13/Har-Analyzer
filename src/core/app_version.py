"""Resolves the running app's version from ``pyproject.toml``.

Embedded HAR metadata (``log._analysis.tool_version``) uses this instead of
a hardcoded constant, so the version tag on every file you standardize
always tracks the app's actual version -- bump it once in ``pyproject.toml``
and every capture tagged after that point reflects it automatically.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, cast

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

# core/app_version.py -> core/ -> repo root. Adjust here if this file moves.
_PYPROJECT_PATH: Path = Path(__file__).resolve().parent.parent / "pyproject.toml"

_FALLBACK_VERSION: str = "0.0.0-unknown"


@lru_cache(maxsize=1)
def get_app_version() -> str:
    """Read the app version from ``pyproject.toml``, cached for the process.

    Looks for ``[project] version`` (PEP 621 / setuptools, hatch, etc.) and
    falls back to ``[tool.poetry] version`` for Poetry-based projects. If
    neither is found, or the file can't be read/parsed, returns a clearly
    fake fallback version rather than raising -- a missing version string
    shouldn't block someone from tagging a HAR file.
    """
    try:
        with _PYPROJECT_PATH.open("rb") as f:
            data = cast(dict[str, Any], tomllib.load(f))
    except (OSError, tomllib.TOMLDecodeError):
        return _FALLBACK_VERSION

    project_table = cast(dict[str, Any], data.get("project", {}) or {})
    project_version = project_table.get("version")
    if isinstance(project_version, str) and project_version:
        return project_version

    tool_table = cast(dict[str, Any], data.get("tool", {}) or {})
    poetry_table = cast(dict[str, Any], tool_table.get("poetry", {}) or {})
    poetry_version = poetry_table.get("version")
    if isinstance(poetry_version, str) and poetry_version:
        return poetry_version

    return _FALLBACK_VERSION
