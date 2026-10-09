#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$REPOSITORY_ROOT/installer/lib/plan.sh"

temporary_root="$(mktemp -d)"
trap 'rm -rf "$temporary_root"' EXIT
export HOME="$temporary_root/home"
export NODE_CORE_DATA_DIR="$HOME/.node-core"
mkdir -p "$HOME" "$NODE_CORE_DATA_DIR"

before="$(find "$HOME" -type f -print | sort)"
plan="$(node_core_plan_installation)"
grep -qx 'mode=install' <<<"$plan"
grep -qx 'manifest_status=missing' <<<"$plan"
grep -qx 'action=install_application' <<<"$plan"
grep -qx 'action=review_missing_kubo' <<<"$plan"
grep -qx 'action=review_missing_ipfs_repository' <<<"$plan"
grep -qx 'action=review_configuration' <<<"$plan"
after="$(find "$HOME" -type f -print | sort)"
[[ "$before" == "$after" ]]

# A complete-looking app with absent launchers yields only the missing actions.
mkdir -p "$NODE_CORE_DATA_DIR/app/node_core" "$NODE_CORE_DATA_DIR/bin" "$NODE_CORE_DATA_DIR/storage" "$NODE_CORE_DATA_DIR/ipfs" "$NODE_CORE_DATA_DIR/runtime"
printf 'print("test")\n' > "$NODE_CORE_DATA_DIR/app/main.py"
printf '{"data_dir":"%s"}\n' "$NODE_CORE_DATA_DIR" > "$NODE_CORE_DATA_DIR/config.json"
printf 'repository config\n' > "$NODE_CORE_DATA_DIR/ipfs/config"
printf '#!/usr/bin/env bash\nexit 0\n' > "$NODE_CORE_DATA_DIR/bin/ipfs"
chmod +x "$NODE_CORE_DATA_DIR/bin/ipfs"
plan="$(node_core_plan_installation)"
grep -qx 'mode=update_or_verify' <<<"$plan"
grep -qx 'action=create_application_launcher' <<<"$plan"
grep -qx 'action=create_update_launcher' <<<"$plan"
! grep -qx 'action=install_application' <<<"$plan"

# Planning must not create launchers, manifests, or change persistent files.
[[ ! -e "$NODE_CORE_DATA_DIR/bin/node-core" ]]
[[ ! -e "$NODE_CORE_DATA_DIR/bin/node-core-update" ]]
[[ ! -e "$NODE_CORE_DATA_DIR/installation-manifest.json" ]]
[[ "$(cat "$NODE_CORE_DATA_DIR/config.json")" == "{\"data_dir\":\"$NODE_CORE_DATA_DIR\"}" ]]

printf 'Installer planning tests passed.\n'
