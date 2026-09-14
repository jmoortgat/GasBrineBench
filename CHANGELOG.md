# Changelog

## Unreleased (pre-v1.0 scaffolding)
- Repository scaffold: schema, contributing rules, validator, CI.
- No data published yet.
- Source manifest: every one of the 5,846 rows now resolves to a real
  published reference, up from 57.4 %. Four placeholder citations and 23
  sources with no bibliographic record at all were identified from the
  primary papers and confirmed against Crossref; see `LEDGER.md`.
- `tools/make_sources.py`: added an evidence-backed source-key correction
  table for `source` cells that name their paper wrongly, and fixed two
  matching defects (variant suffixes longer than one letter, and `\ce{}`
  being mis-read as a cedilla in titles).
