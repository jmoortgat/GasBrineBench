#!/usr/bin/env python3
"""Extract the curated experimental-data transcriptions out of the source trove.

NOTE FOR READERS OF THE PUBLIC REPOSITORY
-----------------------------------------
The tree under `transcriptions/` is already complete and tracked here; you do
not need this script to use it. The script is included as documentation of how
that tree was selected. It reads a private, maintainer-local trove
(`Multi_Salt/source_materials/`) that is NOT part of this repository and will
not exist on your machine, so running it without `--source-materials` will
simply report that the trove was not found. Nothing in this repository depends
on it.

WHY THIS EXISTS
---------------
`Multi_Salt/source_materials/` is a 2.9 GB read-only trove handed over by
collaborators. Almost none of it belongs in version control:

  884 MB  433 .pdf                           not redistributable
  1.0 GB  10,839 .png                        regenerable plot output
  696 MB  3,990 .dat                         solver sweeps / warm-start tables
  228 MB  1,889 .txt  <-- but only 251 KB of these are hand work
   54 MB  a vendored third-party venv        .so/.pyc/.whl
  310 KB  25 .tex                            not redistributable
  6.4 KB  private correspondence             not redistributable

The irreplaceable part is the set of files named `EXP*.txt`: hand-typed
digitisations of experimental tables out of the primary literature. Each one
opens with a `#AUTHOR(YEAR)` provenance header and holds a small tab-separated
block of measured points. They are the provenance root of the benchmark
database and they cannot be regenerated from anything on disk.

Everything else with a `#` header is a `GUESS_*.txt` solver warm start
(92 files) -- machine-written, regenerable, excluded.

This script re-derives the tracked tree from the trove, so the selection rule
is auditable and re-runnable rather than a one-time hand copy.

USAGE
-----
    python3 tools/extract_transcriptions.py [--source-materials PATH] [--check]

`--check` re-hashes the tracked copies against the trove and reports drift
without writing anything.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Maintainer-local trove; absent from this repository and from any clone of it.
DEFAULT_TROVE = os.path.normpath(
    os.path.join(HERE, "..", "Multi_Salt", "source_materials"))
DEST = os.path.join(HERE, "transcriptions")
MANIFEST = os.path.join(DEST, "MANIFEST.tsv")
# Files that live inside DEST but are not transcriptions, so --check must not
# report them as strays.
DEST_OWN_FILES = {"MANIFEST.tsv", "README.md"}

# Directory-name prefixes that mark machine-generated output trees.
OUTPUT_DIR_PREFIXES = ("OPT",)
OUTPUT_DIR_EXACT = ("TXT",)
SKIP_DIRS = {".git", "__pycache__", "venv", "site-packages", ".ipynb_checkpoints"}

# Filesystem copy artifacts -- "EXP1_T383K (copy).txt", "T623K (copy)/".
# Each is a byte-identical duplicate of a sibling, never a distinct
# measurement; 24 of them had reached the published manifest.
COPY_ARTIFACT = "(copy)"

# Superseded transcription trees, skipped in favour of a canonical sibling.
#
# CO2/CPA/{PR,SRK} are the same experimental compilation, filed twice under
# the two cubic backbones it was paired with. The EXP-slot numbering differs
# between them (PR/EXP1 == SRK/EXP2 at 548/573/623 K, PR/EXP2 == SRK/EXP4 at
# 473 K), but the data bodies are identical -- except in two files where SRK
# is strictly lossy, both checked against the original papers on 2026-09-18:
#   T323K/EXP2  Hou 2013 records y_CO2 = 0.97189 +/- 0.00050 at 323.15 K,
#               1.089 MPa (paper Table 2); SRK carries "X" (missing).
#   T538K/EXP1  Todheide & Franck 1963 Table 1b/1c, 265 C column, runs to
#               3500 bar (3000: 55,0/29,2; 3500: 57,0/28,0 mol-%); SRK stops
#               at 2500 bar.
# PR reproduces both in full, so PR alone is published.
SUPERSEDED_DIRS = (os.path.join("EoS", "CO2", "CPA", "SRK"),)

# Individually misfiled transcriptions: the file is real, but the directory
# assigns it the wrong temperature, so extracting it would create a phantom
# isotherm. Each is a byte-identical duplicate of a correctly-filed sibling.
#   PR/T478K/EXP1_T473K.txt -- the eight rows match Todheide 1963 Table 1a's
#   200 C (= 473 K) column exactly (200 bar: 84,5/2,4 ... 3000 bar: 86,7/9,0),
#   and the file is identical to PR/T473K/EXP1_T473K.txt. 478 K is not an
#   isotherm Todheide reports. Verified 2026-09-18.
MISFILED = (os.path.join("EoS", "CO2", "CPA", "PR", "T478K", "EXP1_T473K.txt"),)

# A transcription is never anywhere near this big; the largest real one is ~4 KB.
MAX_BYTES = 100_000


def is_output_path(rel_dir: str) -> bool:
    parts = rel_dir.split(os.sep)
    for seg in parts:
        up = seg.upper()
        if up in OUTPUT_DIR_EXACT:
            return True
        if any(up.startswith(p) for p in OUTPUT_DIR_PREFIXES):
            return True
    return False


def is_excluded_path(rel_dir: str) -> bool:
    """True for copy-artifact and superseded directories (see the constants)."""
    if COPY_ARTIFACT in rel_dir:
        return True
    norm = os.path.normpath(rel_dir)
    return any(norm == d or norm.startswith(d + os.sep) for d in SUPERSEDED_DIRS)


def find_transcriptions(trove: str) -> list[str]:
    """Return trove-relative paths of the curated EXP*.txt transcriptions."""
    found = []
    for dirpath, dirnames, filenames in os.walk(trove):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        rel_dir = os.path.relpath(dirpath, trove)
        if rel_dir != "." and (is_output_path(rel_dir) or is_excluded_path(rel_dir)):
            dirnames[:] = []
            continue
        for fn in sorted(filenames):
            if not fn.upper().startswith("EXP"):
                continue
            if not fn.lower().endswith(".txt"):
                continue
            if COPY_ARTIFACT in fn:
                continue
            if os.path.normpath(os.path.join(rel_dir, fn)) in MISFILED:
                continue
            p = os.path.join(dirpath, fn)
            if os.path.getsize(p) > MAX_BYTES:
                continue
            with open(p, "r", errors="replace") as fh:
                if not fh.readline().startswith("#"):
                    continue
            found.append(os.path.relpath(p, trove))
    return sorted(found)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def describe(path: str) -> tuple[str, int]:
    """Return (source header, number of non-blank data rows)."""
    with open(path, "r", errors="replace") as fh:
        lines = fh.read().splitlines()
    # A file may declare its own temperature after a pipe:
    #   "#CULBERSON(1951) | T=344.26 | 160 degF, Table I"
    # The manifest records the source key only; the declaration is
    # data for the parsers, not part of the source name.
    header = lines[0].lstrip("#").split("|")[0].strip() if lines else ""
    # line 0 = source, line 1 = column names, rest = data
    data = [ln for ln in lines[2:] if ln.strip()]
    return header, len(data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source-materials", default=DEFAULT_TROVE,
                    help="path to the read-only trove (default: ../source_materials)")
    ap.add_argument("--check", action="store_true",
                    help="verify tracked copies against the trove; write nothing")
    args = ap.parse_args()

    trove = os.path.abspath(args.source_materials)
    if not os.path.isdir(trove):
        print(f"error: trove not found: {trove}", file=sys.stderr)
        return 2

    rels = find_transcriptions(trove)
    if not rels:
        print(f"error: no EXP*.txt transcriptions under {trove}", file=sys.stderr)
        return 2

    if args.check:
        missing = drifted = 0
        for rel in rels:
            dst = os.path.join(DEST, rel)
            if not os.path.exists(dst):
                print(f"MISSING  {rel}")
                missing += 1
            elif sha256(dst) != sha256(os.path.join(trove, rel)):
                print(f"DRIFTED  {rel}")
                drifted += 1
        extra = []
        for dirpath, _dn, fns in os.walk(DEST):
            for fn in fns:
                r = os.path.relpath(os.path.join(dirpath, fn), DEST)
                if r in DEST_OWN_FILES or r in rels:
                    continue
                extra.append(r)
        for r in sorted(extra):
            print(f"EXTRA    {r}")
        print(f"\n{len(rels)} expected; {missing} missing, {drifted} drifted, "
              f"{len(extra)} extra")
        return 1 if (missing or drifted or extra) else 0

    total = 0
    rows = []
    for rel in rels:
        src = os.path.join(trove, rel)
        dst = os.path.join(DEST, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        size = os.path.getsize(src)
        total += size
        header, nrows = describe(src)
        rows.append((rel, size, nrows, header, sha256(src)))

    with open(MANIFEST, "w") as fh:
        fh.write("# Generated by tools/extract_transcriptions.py -- do not edit by hand.\n")
        fh.write("# path\tbytes\tdata_rows\tsource_header\tsha256\n")
        for rel, size, nrows, header, digest in rows:
            fh.write(f"{rel}\t{size}\t{nrows}\t{header}\t{digest}\n")

    sources = {r[3] for r in rows}
    print(f"extracted {len(rows)} transcriptions ({total:,} bytes) "
          f"covering {sum(r[2] for r in rows):,} data rows "
          f"from {len(sources)} distinct source headers")
    print(f"  -> {DEST}")
    print(f"  -> {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
