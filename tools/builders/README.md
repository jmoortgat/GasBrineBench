# Builders — kept as documentation, not as a build system

**These five scripts do not run standalone, and are not meant to.** They
import a model-comparison harness (`bench.core.*`) that is not part of this
repository, and they read curation artefacts from maintainer-local paths that
will not exist on your machine. Running them will fail at the first import.

They are here because they are the record of how `../../data/*.csv` was
derived from `../../transcriptions/`, and much of that record exists nowhere
else:

| script | what it documents |
|---|---|
| `build_v0.py` | the main assembly: every dataset block, its source, its unit convention, the molality/mole-fraction conversions, the ion vectors, and the phase-regime screen that assigns the `lle-regime` tag |
| `build_y_h2o.py` | the gas-phase water-content family: which rows are complement-derived (`y_H2O = 1 - y_gas`) and why some of those carry quality `U`, and the cross-author agreement rule that awards `R` |
| `hou2013.py` | the Hou, Maitland & Trusler (2013) tables transcribed **in source**, with the table numbers and page numbers they came from |
| `yh2o_sources_2026.py` | the 2026 water-content additions transcribed **in source**, each with its table number and, importantly, a list of the rows deliberately *not* taken (hydrate equilibria, graphically smoothed values, secondary compilations) and why |
| `quality_pass.py` | the R/T/U assignment pass: the corroboration rule, the removals, and the traced defects. Its output is `../../data/QUALITY.md` |

If you want to check a value, the shortest path is not to run these. It is:

1. find the row's `dataset_id` in `../../data/README.md`, which names the
   paper, table and page;
2. find the `source` header in `../../transcriptions/` to see what was typed;
3. find the citation in `../../SOURCES.md` and obtain the paper.
