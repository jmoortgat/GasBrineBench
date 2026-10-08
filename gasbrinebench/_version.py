"""Single source of truth for the package version.

The package version tracks the *dataset* version, not the code: this package
is a reader for the CSVs in `data/`, and a user who reports
``gasbrinebench.__version__`` is reporting which snapshot of the database they
read. The string is therefore kept identical to the ``version:`` field of
``CITATION.cff`` and to the heading of the current ``CHANGELOG.md`` section,
and ``tests/test_version.py`` fails if the three ever drift apart.

``1.2.1`` adds 146 papers (26,815 rows in 11 families), an optional ``flags``
column and a supplementary tier; see ``CHANGELOG.md``. Some v1.1.1 rows were corrected after checking them against their papers; see ``CHANGELOG.md``.

``1.1.1`` corrects three mixed-brine ion vectors (TEYMOURI_2017 magnesium,
low by a factor 10.15; LI_2004, which mixed molarity and molality; and one
further recipe, all recorded in ``CHANGELOG.md``). No rows are added or
removed. None was catchable internally: every recipe charge-balances, because
chloride was computed from the cations in each case, so the balance closes
around whatever the cations say.

``1.1.0`` adds the CO2 + CH4 + water ternary family: 11,537 rows over 111
published sources, every row resolving to a real reference and every transcription
matching its manifest hash. The Zenodo version DOI is minted on deposit and
added to ``CITATION.cff`` when it exists; it is not a precondition for the
tag, and the tag is what a reader needs in order to name their snapshot.
"""

__version__ = "1.2.1"
