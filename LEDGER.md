# Quality ledger

Every correction, deduplication, quality-code upgrade/downgrade, and
removal is recorded here with its justification. Regenerated entries
from automated passes are marked [auto].

## 2026-09-13 — bibliographic provenance closed out

No data value changed. The work was entirely on the `source` → citation
mapping, and it is recorded here because it changes what the manifest
asserts about where 2,489 rows came from.

- **Coverage** went from 3,357/5,846 rows (57.4 %) carrying a real
  reference to 5,846/5,846 (100 %). Four placeholder citations covering
  1,273 rows were replaced with verified records; 23 source keys with no
  bibliographic record at all, covering 1,216 rows, were resolved.
- **Every identification was made from the primary paper**, read from the
  local literature trove, and checked against the rows' own temperature,
  pressure, salt and composition grid. Every DOI was then confirmed
  against a Crossref record whose title, journal, volume and year match
  the paper identified. Nothing was recalled from memory.
- **Fifteen `source` cells name their paper wrongly** — a misspelt or
  truncated surname, a missing year, an online-first year, or a thesis
  year in place of the published article's. These are rewritten by
  `tools/make_sources.py` before matching, and each rewrite is printed
  with its evidence in the *Source-key corrections* section of
  `SOURCES.md`. The CSV cells are left untouched: their `source` column
  is copied from upstream curation artefacts and would be restored by the
  next rebuild, and two of the strings are asserted verbatim by the
  benchmark's test suite.
- **`OSULLIVAN(1969)` and `OSULLIVAN(1970)` were the same paper** entered
  twice. O'Sullivan & Smith (1970) measured both nitrogen and methane in
  water and in aqueous NaCl over one grid; the 32 methane rows and the
  102 nitrogen rows now share a single citation.
- **Nothing was asserted on author-and-year alone.** `MOHAMMADI(2004)`
  and the bib record `Mohammadi2004eth` are the same authors in the same
  year but different papers; the 22 water-content rows were matched to
  Mohammadi et al., *Ind. Eng. Chem. Res.* **43**(22) 7148 only once the
  paper itself was read and its stated 282.98–313.12 K / 2.846 MPa and
  282.93–293.10 K / 2.99 MPa ranges were found to reproduce the rows'
  own 282.93–313.12 K and 5.06–29.9 bar span exactly.
- **Two generator defects were fixed** in the course of this. Bibtex keys
  whose variant suffix is longer than one letter fell out of the exact
  index and were being rescued by a looser lookup that could not tell
  `Mohammadi2004` from `Mohammadi2004eth`; and `\ce{...}` in a title was
  being read as a cedilla, which is where the manifest's old `eCO2` and
  `eSrCl2` came from.
- **Six works have no DOI** and are reported as such: two doctoral theses
  (Kobayashi 1951, Teymouri 2017 — the latter with its repository
  handle), two association research reports (Gillespie 1980, Devaney
  1978 — the former with its OSTI record), and two papers in journals
  never retrospectively registered (Umano & Nakano 1958, Ipatev 1934).
  No substitute identifier was supplied for any of them.
- **Umano & Nakano (1958) is recorded without a title.** The copy held is
  the reprint in IUPAC Solubility Data Series volume 24, whose house
  style omits titles, so none is known and none was invented.
