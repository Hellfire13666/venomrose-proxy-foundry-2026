#!/usr/bin/env bash
set -euo pipefail
folder="${VENOMROSE_REPORTS:-$HOME/VenomRoseReports}"
if [[ "${1:-}" == "--file" && -n "${2:-}" ]]; then
  file="$2"
else
  file="$(find "$folder" -maxdepth 1 -type f -name 'VENOMROSE-*.html' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)"
fi
if [[ -z "${file:-}" || ! -f "$file" ]]; then echo 'No VENOMROSE HTML report found.' >&2; exit 1; fi
printf '🥀 REPORT: %s\n' "$file"
if command -v xdg-open >/dev/null; then xdg-open "$file" >/dev/null 2>&1 || printf 'Open manually: %s\n' "$file"; else printf 'Open manually: %s\n' "$file"; fi
