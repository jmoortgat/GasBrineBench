"""Single source of truth for the package version.

The package version tracks the *dataset* version, not the code: this package
is a reader for the CSVs in `data/`, and a user who reports
``gasbrinebench.__version__`` is reporting which snapshot of the database they
read. The string is therefore kept identical to the ``version:`` field of
``CITATION.cff`` and to the heading of the current ``CHANGELOG.md`` section,
and ``tests/test_version.py`` fails if the three ever drift apart.

``0.9.0-pre`` is the pre-release state described in ``CHANGELOG.md``: the
database is complete and in the repository, the v1.0 release (and with it the
Zenodo version DOI) is still in preparation.
"""

__version__ = "0.9.0-pre"
