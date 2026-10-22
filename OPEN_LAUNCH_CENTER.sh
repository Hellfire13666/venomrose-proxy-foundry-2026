#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
FILE="$HERE/VENOMROSE-LAUNCH-CENTER.html"
if [[ ! -f "$FILE" ]]; then echo "VENOMROSE launch center missing: $FILE" >&2; exit 1; fi
printf '🥀 VENOMROSE LAUNCH CENTER: %s\n' "$FILE"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$FILE" >/dev/null 2>&1 || printf 'Open manually: %s\n' "$FILE"
else
  printf 'Open manually: %s\n' "$FILE"
fi
