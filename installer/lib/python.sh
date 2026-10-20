#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS installer helpers cannot run as root. Use the normal user account without sudo.\\n' >&2
  return 1 2>/dev/null || exit 1
fi

ensure_python_environment() {
  local requirements_file="$1"
  local environment="$NODE_CORE_DATA_DIR/runtime/node-core-venv"
  [[ -f "$requirements_file" ]] || {
    printf 'Python requirements file not found: %s\n' "$requirements_file" >&2
    return 1
  }
  mkdir -p "$NODE_CORE_DATA_DIR/runtime"
  if [[ ! -x "$environment/bin/python" ]]; then
    python3 -m venv "$environment" || {
      printf 'Could not create the private Python environment. Install the python3-venv package and retry.\n' >&2
      return 1
    }
  fi
  if grep -Eq '^[[:space:]]*[^#[:space:]]' "$requirements_file"; then
    local wheel_dir="$NODE_CORE_DATA_DIR/app/installer/vendor/python-wheels"
    if [[ -d "$wheel_dir" ]] && find "$wheel_dir" -maxdepth 1 -type f -name '*.whl' -print -quit | grep -q .; then
      "$environment/bin/python" -m pip install --disable-pip-version-check --no-index --find-links "$wheel_dir" --upgrade -r "$requirements_file" || {
        printf 'Bundled Python dependencies could not be installed offline.\n' >&2
        return 1
      }
    else
      "$environment/bin/python" -m pip install --disable-pip-version-check --upgrade -r "$requirements_file" || {
      printf 'Could not install Node Core OS Python dependencies in its private environment.\n' >&2
      return 1
      }
    fi
  fi
  if grep -Eiq '^[[:space:]]*cryptography([<=>!~[:space:]]|$)' "$requirements_file"; then
    "$environment/bin/python" -c 'import cryptography; print("Verified cryptography:", cryptography.__version__)' || {
      printf 'The cryptography dependency failed its import verification.\n' >&2
      return 1
    }
  fi
}

install_application() {
  local source_dir="$1" target_dir="$NODE_CORE_DATA_DIR/app"
  if [[ -L "$target_dir" || ( -e "$target_dir" && ! -d "$target_dir" ) ]]; then
    printf 'Unsafe application path: %s is not a real directory.\n' "$target_dir" >&2
    return 1
  fi
  if [[ -d "$target_dir" ]] && [[ -n "$(find "$target_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    printf 'An application already exists at %s. Use node-core-update to update it safely.\n' "$target_dir" >&2
    return 1
  fi
  mkdir -p "$target_dir"
  cp -R "$source_dir"/. "$target_dir"/
  rm -rf "$target_dir/.git"
}
create_launcher() {
  cat > "$NODE_CORE_DATA_DIR/bin/node-core" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export NODE_CORE_CONFIG="$NODE_CORE_DATA_DIR/config.json"
exec "$NODE_CORE_DATA_DIR/runtime/node-core-venv/bin/python" "$NODE_CORE_DATA_DIR/app/main.py" "$@"
EOF
  chmod +x "$NODE_CORE_DATA_DIR/bin/node-core"

  cat > "$NODE_CORE_DATA_DIR/bin/node-core-update" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec bash "$NODE_CORE_DATA_DIR/app/installer/update.sh" "$@"
EOF
  chmod +x "$NODE_CORE_DATA_DIR/bin/node-core-update"

  cat > "$NODE_CORE_DATA_DIR/bin/hashpaper" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export NODE_CORE_DATA_DIR="$NODE_CORE_DATA_DIR"
export PATH="$NODE_CORE_DATA_DIR/runtime/opentimestamps-venv/bin:$PATH"
exec python3 "$NODE_CORE_DATA_DIR/app/applications/hashpaper/main.py" "\$@"
EOF
  chmod 700 "$NODE_CORE_DATA_DIR/bin/hashpaper"
}
write_config() {
  local ipfs_executable
  if [[ -n "${NODE_CORE_KUBO_EXECUTABLE:-}" ]]; then
    ipfs_executable="$NODE_CORE_KUBO_EXECUTABLE"
  elif [[ -n "${TERMUX_VERSION:-}" && -x "${PREFIX:-}/bin/ipfs" ]]; then
    ipfs_executable="$PREFIX/bin/ipfs"
  else
    ipfs_executable="$NODE_CORE_DATA_DIR/bin/ipfs"
  fi
  cat > "$NODE_CORE_DATA_DIR/config.json" <<EOF
{
  "data_dir": "$NODE_CORE_DATA_DIR",
  "local_storage_path": "$NODE_CORE_DATA_DIR/storage",
  "ipfs_repo_path": "$NODE_CORE_DATA_DIR/ipfs",
  "ipfs_api": "$NODE_CORE_KUBO_API",
  "ipfs_gateway": "$NODE_CORE_KUBO_GATEWAY",
  "ipfs_executable": "$ipfs_executable",
  "ipfs_profile": "unixfs-v1-2025"
}
EOF
}
