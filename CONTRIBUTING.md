# Contributing data to GasBrineBench

Contributions land as pull requests that add rows to the family
csvs under `data/` (or a new family csv following `SCHEMA.md`).

## What a PR must contain

1. New rows following the schema exactly — every row with `dataset_id`,
   `source`, `quality` and `tag` filled (`T` is the default for new
   single-source data, do not self-assign `R`; `test-only` is the default
   tag).
2. The full reference added to `bib/references.bib`, keyed so that
   `tools/make_sources.py` resolves your `source` cells onto it, plus the
   regenerated `SOURCES.md` and `SOURCES.bib` committed alongside
   (`python3 tools/make_sources.py`). Do not hand-edit either generated file.
3. A new entry in the *Provenance per dataset_id* table of `data/README.md`:
   which paper, which table or figure, which page, what unit conversion was
   applied, and what you deliberately skipped.
4. The raw transcription under `transcriptions/`, headed `#AUTHOR(YEAR)`, if
   the rows were typed from a printed table. Add it to
   `transcriptions/MANIFEST.tsv`.
5. A one-paragraph note in the PR description: what the data are,
   how they were transcribed (table vs digitized), and any known
   caveats stated by the original authors.
6. A passing validation run: `python3 tools/validate.py` (also runs
   as CI on the PR). It checks schema conformance, units/ranges, the
   gas/gas-free column convention, sibling-row consistency, same-source
   duplicate collisions against existing rows, the quality and tag
   vocabularies, and that every `source` cell resolves to a real record.
7. A passing package run: `python3 -m pytest tests -q` and
   `python3 -m pytest --doctest-modules gasbrinebench -q`, both also in CI.
   The tests assert the row inventory and several per-family counts, so a PR
   that adds rows will need those expectations updated in the same commit —
   that is deliberate, it makes a silent row change impossible.

If your contribution is to the `gasbrinebench` package rather than to the
data, keep the vocabularies in `gasbrinebench/vocab.py` in step with
`SCHEMA.md` and `tools/validate.py`, and add a test. Docstring examples are
run as doctests, so they have to be true.

## What maintainers do

- Review provenance (spot-check against the source), run the
  cross-source consistency pass, assign/confirm the quality code,
  and add a `LEDGER.md` entry for anything nontrivial.
- Batch merged contributions into the next tagged release
  (Zenodo-archived with a version DOI); contributors are
  acknowledged in the release notes.

## Ground rules

- **Never add a publisher PDF, a manuscript, a draft, or any other
  copyrighted or unpublished material.** `.gitignore` is an allowlist and will
  block them, but the rule matters more than the mechanism: this repository
  redistributes transcribed numbers with attribution, never the papers
  themselves. If your PR needs a new *kind* of file, add its path to the
  allowlist in the same PR and say why.
- Experimental values only (see SCHEMA.md rule 3).
- Never modify existing rows in a data PR; corrections are separate
  PRs with a ledger entry explaining the defect.
- Disagreements about a data point's quality code: open an issue
  citing the evidence.
