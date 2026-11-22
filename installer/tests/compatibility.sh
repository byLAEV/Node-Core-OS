#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHONPATH="$REPOSITORY_ROOT" python3 -m unittest tests.test_compatibility -v
python3 - "$REPOSITORY_ROOT/compatibility/manifest.json" <<'PY'
import json,sys
m=json.load(open(sys.argv[1],encoding="utf-8"))
assert set(m["supported_environments"]) == {"gnu_linux"}
print("PASS: compatibility manifest declares GNU/Linux only.")
PY
