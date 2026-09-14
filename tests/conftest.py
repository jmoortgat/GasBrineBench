"""Shared fixtures. Puts the repository root on ``sys.path``.

The package is not installed; it is imported from the clone, exactly as a
reader following the README would import it. Running ``python3 -m pytest``
from the repository root therefore needs nothing but pandas and pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gasbrinebench as gbb  # noqa: E402


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def all_rows():
    """Every row in the database, including the lle-regime ones."""
    return gbb.load(exclude_tags=None)


@pytest.fixture(scope="session")
def default_rows():
    """What the default loader hands back."""
    return gbb.load()
