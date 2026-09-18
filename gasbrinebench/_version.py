"""Single source of truth for the package version.

The package version tracks the *dataset* version, not the code: this package
is a reader for the CSVs in `data/`, and a user who reports
``gasbrinebench.__version__`` is reporting which snapshot of the database they
read. The string is therefore kept identical to the ``version:`` field of
``CITATION.cff`` and to the heading of the current ``CHANGELOG.md`` section,
and ``tests/test_version.py`` fails if the three ever drift apart.

``1.0.0`` is the first released snapshot: 11,444 rows over 109 published
sources, every row resolving to a real reference and every transcription
matching its manifest hash. The Zenodo version DOI is minted on deposit and
added to ``CITATION.cff`` when it exists; it is not a precondition for the
tag, and the tag is what a reader needs in order to name their snapshot.
"""

__version__ = "1.0.0"
