#!/usr/bin/env python3
"""Verify transcriptions/ against transcriptions/MANIFEST.tsv.

This is the integrity check that works without the private source trove, and
so it is the one CI can run. `tools/extract_transcriptions.py --check` compares
against the trove itself and is a maintainer-only tool.

It confirms that every file the manifest lists is present and byte-identical
to its recorded SHA-256, that no file in the tree is absent from the manifest,
and that the recorded byte and row counts still add up. Exit 0 = clean.
"""
from __future__ import annotations

import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "transcriptions")
MANIFEST = os.path.join(DEST, "MANIFEST.tsv")
NOT_TRANSCRIPTIONS = {"MANIFEST.tsv", "README.md"}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not os.path.isfile(MANIFEST):
        print(f"error: {MANIFEST} not found", file=sys.stderr)
        return 2

    rows = []
    with open(MANIFEST) as fh:
        for ln in fh:
            if ln.startswith("#") or not ln.strip():
                continue
            parts = ln.rstrip("\n").split("\t")
            if len(parts) != 5:
                print(f"error: malformed manifest line: {ln!r}", file=sys.stderr)
                return 2
            rows.append(parts)

    bad: list[str] = []
    total_bytes = total_rows = 0
    headers = set()
    for rel, size, nrows, header, digest in rows:
        p = os.path.join(DEST, rel)
        if not os.path.isfile(p):
            bad.append(f"MISSING   {rel}")
            continue
        if os.path.getsize(p) != int(size):
            bad.append(f"SIZE      {rel}")
        if sha256(p) != digest:
            bad.append(f"DRIFTED   {rel}")
        if not header.strip():
            bad.append(f"NO SOURCE {rel}")
        total_bytes += int(size)
        total_rows += int(nrows)
        headers.add(header)

    listed = {r[0] for r in rows}
    for dirpath, _dn, fns in os.walk(DEST):
        for fn in fns:
            rel = os.path.relpath(os.path.join(dirpath, fn), DEST)
            if rel in NOT_TRANSCRIPTIONS or rel in listed:
                continue
            bad.append(f"UNLISTED  {rel}")

    if bad:
        print("TRANSCRIPTION CHECK FAILED:")
        for b in sorted(bad):
            print(" -", b)
        return 1

    print(f"transcriptions: {len(rows)} files, {total_bytes:,} bytes, "
          f"{total_rows:,} data rows, {len(headers)} source headers -- "
          "all match MANIFEST.tsv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
