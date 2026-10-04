# v1.2 builder

Unlike `tools/builders/`, these scripts **run from this repository alone**.
They need `numpy`, `pandas`, `iapws` (IAPWS-95 water properties) and `gsw`
(TEOS-10 seawater density), and read the tables in `transcriptions_v1_2/`.

| script | does | runs here |
|---|---|---|
| `gbb12_build.py` | reads every `table_N.csv` + `mapping_N.json` + `paper.json` and converts each row to the schema, holding back with a reason every row it cannot convert without a model, an assumed density or an assumed pressure | yes |
| `gbb12_supp.py` | writes `supplementary/supplementary_measurements.csv` from the rows the builder could not convert | yes |
| `gbb12_quality.py` | the cross-source R/T/U rules of `data/QUALITY.md` | yes |
| `gbb12_core.py`, `gbb12_loader.py` | unit and composition conversions; the mapping reader | (imported) |
| `gbb12_corrections.py` | the corrections to v1.1.1 rows and the quality and flag edits found by checking the consensus outliers against the papers; each guarded by the value it expects | (imported by the release script) |
| `gbb12_consensus.py` | the inter-source consensus statistic (`data/consensus/`) | yes |
| `gbb12_release.py` | merges the v1.1.1 CSVs with the new rows, assigns citation keys, applies the quality rules, writes `data/` and `bib/references_v1_2.bib` | needs the maintainers' work area (v1.1.1 from git, Crossref cache) |
| `gbb12_meta.py` | fetches Crossref metadata and OpenAlex citation counts by DOI | needs network |
| `SPEC.md` | the mapping-file format | |

Reproduce the new rows and the supplementary tier (byte-identical to what the
release script consumed):

```
python3 tools/builders_v1_2/gbb12_build.py --extract transcriptions_v1_2 --out /tmp/gbb12
python3 tools/builders_v1_2/gbb12_supp.py  --extract transcriptions_v1_2 --out /tmp/gbb12_supp
```

`/tmp/gbb12/new_rows.csv` holds the 17,150 rows built from the 353
transcribed tables; 739 of them (gas mixtures and two-dissolved-gas tables) and
172 exact duplicates are removed by `gbb12_release.py` and listed in
`LEDGER.md`, and the rest become the 16,223 rows added to the families (15,529 net of the 2 v1.1.1 rows removed).
