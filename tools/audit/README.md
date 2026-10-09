# Audit of the data against the papers

These files document the comparison of every datapoint with its paper and the
random audits that estimated the remaining error (see `CHANGELOG.md`). They are
published as they were run, so that the procedure can be inspected. They cannot
be rerun from this repository alone: they read the maintainers' archive of the
papers (not redistributed) and use local paths, which are replaced here by
`<repo>`, `<work>`, `<papers>` and `<scratch>`.

| file | content |
|---|---|
| `gbb12_fullaudit_packets.py` | splits the data by cited paper into packets of about 700 datapoints for the readers of the full audit |
| `BRIEF_full_audit.md`, `BRIEF_full_audit_fixes.md` | the written instructions given to the readers who compared every datapoint with the paper, and to those who proposed corrections |
| `gbb12_audit_sample.py`, `BRIEF_random_audit.md` | the seeded, stratified random sample of datapoints and the instructions for the readers of the blind random audits |
| `gbb12_audit_analyze.py` | the estimates of the error rate from the audit results |
| `gbb12_dupes.py` | the detection of exact duplicate datapoints |

The audit readers were language-model agents (Claude, Anthropic, run through
Claude Code). They proposed verdicts and corrections only. The corrections were
applied by a script (`tools/builders_v1_2/gbb12_audit_fixes.py`) under written
rules, each guarded by the value it expects, and every correction is listed with
its old value and reason in `data/provenance/audit_corrections.csv`; the status
of each datapoint is in `data/provenance/audit_status.csv`.
