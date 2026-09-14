#!/usr/bin/env python3
"""Fail if git is tracking anything this repository must never publish.

`.gitignore` is an allowlist, which stops accidents at `git add` time. This is
the second line: it looks at what is actually tracked, so a file forced in with
`git add -f`, or inherited from an earlier commit, still gets caught before the
push.

The repository is public and is developed alongside material that may not be
redistributed. None of that may ever appear here, whatever the ignore rules
happen to say on the day.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: extensions that can never be part of this dataset
BANNED_EXT = {
    ".pdf", ".ps", ".eps", ".djvu", ".tex", ".bbl", ".doc", ".docx", ".odt",
    ".rtf", ".pptx", ".eml", ".mbox", ".png", ".jpg", ".jpeg", ".gif", ".tif",
    ".tiff", ".parquet", ".dat", ".npz", ".npy", ".mat", ".sav", ".h5",
    ".zip", ".tar", ".gz", ".7z", ".so", ".dylib", ".dll", ".a", ".exe",
    ".whl", ".pyc",
}

#: path components that only ever occur in the non-redistributable trove
BANNED_DIRS = {
    "source_materials", "source_data", "papers", "paper", "drafts", "reviews",
    "correspondence", "emails", "manuscripts", "TXT", "__pycache__",
}

#: directories whose contents are enumerated exactly
ALLOWED_TOP = {
    "data", "bib", "tools", "transcriptions", ".github",
}

#: files permitted at the repository root
ALLOWED_ROOT_FILES = {
    "README.md", "SCHEMA.md", "LEDGER.md", "CHANGELOG.md", "CONTRIBUTING.md",
    "LICENSE", "CITATION.cff", "SOURCES.md", "SOURCES.bib", ".gitignore",
}


def tracked() -> list[str]:
    out = subprocess.run(["git", "-C", ROOT, "ls-files"],
                         capture_output=True, text=True, check=True)
    return [p for p in out.stdout.splitlines() if p]


def main() -> int:
    bad: list[str] = []
    for path in tracked():
        parts = path.split("/")
        ext = os.path.splitext(path)[1].lower()
        if ext in BANNED_EXT:
            bad.append(f"{path}  (banned extension {ext})")
        hit = [p for p in parts[:-1] if p in BANNED_DIRS or p.startswith("OPT")]
        if hit:
            bad.append(f"{path}  (banned path component {hit[0]!r})")
        if len(parts) == 1:
            if path not in ALLOWED_ROOT_FILES:
                bad.append(f"{path}  (unexpected file at the repository root)")
        elif parts[0] not in ALLOWED_TOP:
            bad.append(f"{path}  (unexpected top-level directory {parts[0]!r})")

    if bad:
        print("TRACKED-FILE CHECK FAILED -- these must not be in this repo:")
        for b in sorted(set(bad)):
            print(" -", b)
        return 1

    n = len(tracked())
    print(f"tracked-file check: {n:,} tracked files, none banned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
