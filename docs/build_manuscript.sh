#!/usr/bin/env bash
# Builds the submittable manuscript (.docx) from docs/Paper-Draft.md.
# Requires: pandoc, python-docx.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-Manuscript.docx}"
awk '/<!-- MANUSCRIPT-START -->/{p=1; next} p{print}' docs/Paper-Draft.md > /tmp/manuscript_build.md
pandoc /tmp/manuscript_build.md -o "$OUT" --standalone -V papersize:letter --resource-path=.
python3 docs/assets/fix_docx_tables.py "$OUT"
echo "wrote $OUT"
