#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
echo '🥀 VENOMROSE // OFFLINE RELEASE CHECK'
./RUN_TESTS.sh
./OPEN_VENOMROSE.sh --doctor
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT
./OPEN_VENOMROSE.sh --demo --out "$TEMP_DIR" --color never
python3 - "$TEMP_DIR" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1]); f=list(p.glob('VENOMROSE-*.json'))
assert len(f)==1
j=json.loads(f[0].read_text());assert j['mode'].startswith('SYNTHETIC')
assert j['summary']['unique']==4
assert j['summary']['multi_source']==2
assert all(list(p.glob('*.{}'.format(ext))) for ext in ('txt','html','csv'))
page=next(p.glob('*.html')).read_text()
assert 'VENOMROSE' in page
assert 'src="data:image/png;base64,' in page
assert 'https://github.com/Hellfire13666/venomrose-proxy-foundry-2026' in page
print('PASS: synthetic report verified, including JSON/CSV/TXT/HTML')
PY
printf 'PASS: VENOMROSE release checks completed offline.\n'
