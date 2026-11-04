#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
REPORT_FILE="$(mktemp)"
trap 'rm -f "$REPORT_FILE"' EXIT
set +e
PYTHONPATH="$REPOSITORY_ROOT" NODE_CORE_ACTIVE_SHELL=bash python3 -m node_core.compatibility \
  --manifest "$REPOSITORY_ROOT/compatibility/manifest.json" --mode diagnose --json > "$REPORT_FILE"
status=$?
set -e
[[ "$status" -eq 0 || "$status" -eq 2 || "$status" -eq 3 ]]
python3 - "$REPORT_FILE" <<'PY'
import json,sys
from pathlib import Path
result=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert result["compatibility_contract"]=="NCTCL-1"
assert result["status"] in {"ready","requires_preparation","unsupported"}
assert "environment" in result and "recommended_actions" in result
print("Terminal compatibility CLI: valid machine-readable report")
print("Detected profile:",result["profile"])
print("Decision:",result["status"])
PY
