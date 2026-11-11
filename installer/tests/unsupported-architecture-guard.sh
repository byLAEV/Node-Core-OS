#!/usr/bin/env bash
# End-to-end fail-closed checks for unsupported architectures.
# This test runs the real installer and updater as an ordinary user. A temporary
# Python sitecustomize module changes only the detected host architecture; no
# production code or host machine configuration is modified.
set -Eeuo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TEMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEMP_ROOT"' EXIT

test "$(id -u)" -ne 0 || {
  printf 'ERROR: unsupported-architecture tests must run as a normal user.\n' >&2
  exit 1
}

ORIGINAL_PATH="$PATH"

snapshot_tree() {
  local root="$1"
  local prefix="$2"
  (
    cd "$root"
    find . -mindepth 1 -printf '%y %m %u:%g %p\n' | LC_ALL=C sort
  ) > "$prefix.tree"
  (
    cd "$root"
    find . -type f -print0 | LC_ALL=C sort -z | xargs -0 -r sha256sum
  ) > "$prefix.sha256"
}

run_case() (
  set -Eeuo pipefail
  local operation="$1"
  local profile="$2"
  local architecture="$3"
  local case_name="$4"
  local case_root="$TEMP_ROOT/$case_name"
  local home="$case_root/home"
  local data="$home/.node-core"
  local shim="$case_root/python-shim"
  local log="$case_root/$operation.log"
  local before="$case_root/before"
  local after="$case_root/after"
  local status

  mkdir -p "$home" "$shim"
  cat > "$shim/sitecustomize.py" <<'PY'
import os
import platform

machine = os.environ.get("NODE_CORE_TEST_UNSUPPORTED_ARCH")
if machine:
    platform.system = lambda: "Linux"
    platform.machine = lambda: machine
PY

  export HOME="$home"
  export NODE_CORE_DATA_DIR="$data"
  export NODE_CORE_TEST_UNSUPPORTED_ARCH="$architecture"
  export PYTHONPATH="$shim${PYTHONPATH:+:$PYTHONPATH}"
  export PATH="$ORIGINAL_PATH"

  if [[ "$profile" == "termux" ]]; then
    export TERMUX_VERSION="test-termux"
    export PREFIX="$case_root/termux-prefix"
    mkdir -p "$PREFIX/bin"
    cat > "$PREFIX/bin/pkg" <<'PKG'
#!/usr/bin/env bash
exit 0
PKG
    chmod 700 "$PREFIX/bin/pkg"
    export PATH="$PREFIX/bin:$PATH"
  else
    unset TERMUX_VERSION PREFIX || true
  fi

  if [[ "$operation" == "update" ]]; then
    mkdir -p "$data/app" "$data/storage" "$data/ipfs" "$data/runtime"
    printf 'synthetic installed application\n' > "$data/app/main.py"
    printf 'synthetic user data\n' > "$data/storage/user-data.txt"
    printf '{"Identity":{"PeerID":"synthetic-unsupported-arch"}}\n' > "$data/ipfs/config"
    printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n' > "$data/runtime/node-core-commit"
    snapshot_tree "$data" "$before"
  fi

  set +e
  if [[ "$operation" == "install" ]]; then
    bash "$REPOSITORY_ROOT/installer/install.sh" > "$log" 2>&1
  else
    bash "$REPOSITORY_ROOT/installer/update.sh" > "$log" 2>&1
  fi
  status=$?
  set -e

  if [[ "$status" -ne 3 ]]; then
    cat "$log" >&2
    printf 'ERROR: %s/%s (%s) should exit 3, got %s.\n' "$operation" "$profile" "$architecture" "$status" >&2
    exit 1
  fi
  grep -Fq 'Arquitectura no soportada' "$log" || {
    cat "$log" >&2
    printf 'ERROR: compatibility preflight did not report the unsupported architecture.\n' >&2
    exit 1
  }

  if [[ "$operation" == "install" ]]; then
    test ! -e "$data" || {
      printf 'ERROR: clean installation changed the destination before rejecting the architecture.\n' >&2
      exit 1
    }
  else
    snapshot_tree "$data" "$after"
    cmp -s "$before.tree" "$after.tree" || {
      diff -u "$before.tree" "$after.tree" >&2 || true
      printf 'ERROR: updater changed the installation tree before rejecting the architecture.\n' >&2
      exit 1
    }
    cmp -s "$before.sha256" "$after.sha256" || {
      diff -u "$before.sha256" "$after.sha256" >&2 || true
      printf 'ERROR: updater changed persistent file contents before rejecting the architecture.\n' >&2
      exit 1
    }
    test ! -e "$data/runtime/update" || {
      printf 'ERROR: updater created recovery or staging state before rejecting the architecture.\n' >&2
      exit 1
    }
  fi

  printf 'PASS: %s rejects %s/%s before changing the destination.\n' "$operation" "$profile" "$architecture"
)

# Unsupported GNU/Linux architecture: validate both clean-install and update entry points.
run_case install gnu_linux riscv64 gnu-linux-install
run_case update gnu_linux riscv64 gnu-linux-update

# Termux is supported only on Android ARM64. A non-ARM64 Termux environment
# must be rejected before installer or updater mutation.
run_case install termux x86_64 termux-install
run_case update termux x86_64 termux-update

printf 'All unsupported-architecture fail-closed tests passed (uid=%s).\n' "$(id -u)"
