#!/bin/sh
# Post-render cleanup for the Quarto docs site: keep only the rendered pages
# and their figures. Quarto copies project files it treats as resources into
# _site/; the data, code and raw markdown are served from GitHub and Zenodo.
# Best effort: a missing path is not a failure.

TARGET_DIR="${QUARTO_PROJECT_OUTPUT_DIR:-_site}"
[ -d "$TARGET_DIR" ] || exit 0
cd "$TARGET_DIR" || exit 0

rm -rf gasbrinebench tests transcriptions_v1_2 __pycache__
find . -name "*.csv" -delete
find . -name "*.py" -delete
find . -name "*.ipynb" -delete
find . -name "*.md" -delete
exit 0
