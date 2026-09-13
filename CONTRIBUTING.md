# Contributing data to GasBrineBench

Contributions land as pull requests that add rows to the family
csvs under `data/` (or a new family csv following `SCHEMA.md`).

## What a PR must contain

1. New rows following the schema exactly — every row with `source`,
   `provenance`, and `quality` filled (`T` is the default for new
   single-source data; do not self-assign `R`).
2. The full reference added to `SOURCES.bib`.
3. A one-paragraph note in the PR description: what the data are,
   how they were transcribed (table vs digitized), and any known
   caveats stated by the original authors.
4. A passing validation run: `python tools/validate.py` (also runs
   as CI on the PR). It checks schema conformance, units/ranges,
   sibling-row consistency, duplicate collisions against existing
   rows, and bib completeness.

## What maintainers do

- Review provenance (spot-check against the source), run the
  cross-source consistency pass, assign/confirm the quality code,
  and add a `LEDGER.md` entry for anything nontrivial.
- Batch merged contributions into the next tagged release
  (Zenodo-archived with a version DOI); contributors are
  acknowledged in the release notes.

## Ground rules

- Experimental values only (see SCHEMA.md rule 3).
- Never modify existing rows in a data PR; corrections are separate
  PRs with a ledger entry explaining the defect.
- Disagreements about a data point's quality code: open an issue
  citing the evidence.
