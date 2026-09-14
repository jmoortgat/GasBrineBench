# Transcriptions — the hand-typed source tables

These are the hand-typed digitisations of the experimental tables in the
primary literature. They sit underneath every row of `../data/`: the builders
in `../tools/builders/` read them, convert units, and emit the family CSVs.
They are the bottom of the provenance chain, and unlike everything above them
they cannot be regenerated from anything — they are somebody's typing, checked
against the printed page.

**819 files · 257 KB · 8,565 data rows · 124 distinct literature sources.**

They are included here so the chain is inspectable end to end:

    transcriptions/EoS/.../EXP*.txt   ->   data/*.csv   ->   SOURCES.md

## What a transcription looks like

```
#WIEBE(1934)
P [bar]    xh_W    yw_H
25.3	0.000328	X
50.7	0.000654	X
101.3	0.001301	X
```

Line 1 is the provenance header naming the primary source. Line 2 names the
columns. The rest is the measured block. `X` marks a quantity the source did
not report.

The `#AUTHOR(YEAR)` header is the same string that appears in the `source`
column of the CSVs, so any row of the database can be traced back to the file
it was typed into. `SOURCES.md` then maps that string to the full
bibliographic record.

## Layout

The source trove's directory structure is preserved verbatim, because the path
itself carries information the file does not — gas, co-solute, salt, and
isotherm all live in the path:

```
transcriptions/EoS/H2/H2-Water/348K/EXP1_T348K.txt
transcriptions/EoS/CO2/eCPA/SINGLE_SALT/...
transcriptions/EoS/CH4/CH4-Brine/S_CaCl/...
```

| tree | files | what |
|---|---:|---|
| `EoS/CO2/eCPA` | 375 | CO2 in single- and mixed-salt brines |
| `EoS/CO2/CPA` | 183 | CO2 in pure water |
| `EoS/CH4/CH4-Water` | 143 | CH4 in pure water |
| `EoS/H2/H2-Water` | 62 | H2 in pure water |
| `EoS/CH4/CH4-Brine` | 37 | CH4 in brines |
| `EoS/H2/H2-CO2` | 10 | H2–CO2 binary |
| `EoS/H2/H2-Brine` | 9 | H2 in NaCl brine |

`MANIFEST.tsv` lists every file with its byte count, row count, source header,
and SHA-256, so the tree can be checked for drift without the trove.

## How the selection was made

`../tools/extract_transcriptions.py` derived this tree from a private,
maintainer-local trove of collaborator material. **That trove is not part of
this repository and the script will not run without it**; it is kept as
documentation of the selection rule, which is deliberately narrow:

> a file is a curated transcription if it is named `EXP*.txt`, is smaller than
> 100 KB, opens with a `#` provenance header, and does not sit under an `OPT*/`
> or `TXT/` directory.

That rule was checked against the alternatives. Selecting on the `#` header
alone would additionally sweep in 92 `GUESS_*.txt` solver warm-start files,
which are machine-written and regenerable. Selecting on the `EXP` name alone
would sweep in 16 files of ~132 KB each under `EoS/CH4/CCW/EXP/`, which despite
the directory name are solver output grids, not measurements.

## What is deliberately not here, and why

The trove these were selected out of is 2.9 GB. 99.99 % of it stays out, and
most of it could not lawfully be published at all:

| excluded | size | reason |
|---|---:|---|
| 433 publisher PDFs | 884 MB | copyright — never redistributable |
| 10,839 `.png` | 1.0 GB | plot output, regenerable |
| 3,990 `.dat` | 696 MB | solver sweeps and warm-start tables, regenerable |
| the other 1,070 `.txt` (`OPT*/`, `TXT/`, `GUESS_*`) | 228 MB | solver output, regenerable |
| a vendored third-party `venv/` | 54 MB | not ours to ship |
| 25 `.tex` under `papers/` and `reports/` | 310 KB | collaborators' unpublished manuscripts |
| `emails/email_copies.txt` | 6 KB | private correspondence |

The repository's `.gitignore` is deny-by-default precisely so that none of
that can arrive here by accident: nothing is trackable unless it is named in
the allowlist, and `*.pdf`, `*.tex` and the trove's directory names are
re-blocked *after* the allowlist so no future `git add -A` can leak a
copyrighted page.

## On what these numbers are

The values in these files are measurements published by the authors named in
each header. We typed them; we do not own them. They are redistributed here as
transcribed data with attribution to the original experimentalists, who are
the people to cite — see `../SOURCES.md`.
