#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
bash -n "$ROOT/installer/update-v2.sh"
python3 -m json.tool "$ROOT/installer/version-v2.json" >/dev/null
grep -q 'Kubo/IPFS is excluded' "$ROOT/installer/update-v2.sh"
grep -q 'node-core-version' "$ROOT/installer/update-v2.sh"
printf '%s\n' 'Update V2 syntax and manifest checks passed.'
