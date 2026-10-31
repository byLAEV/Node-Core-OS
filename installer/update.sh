#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" == "0" ]]; then
  printf 'Node Core OS is strictly user-level software; root execution is forbidden. Run as your normal user without sudo.\n' >&2
  exit 1
fi


NODE_CORE_REPOSITORY="${NODE_CORE_REPOSITORY:-https://github.com/byLAEV/Node-Core-OS}"
NODE_CORE_BRANCH="${NODE_CORE_BRANCH:-main}"
NODE_CORE_DATA_DIR="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
NODE_CORE_APP_DIR="$NODE_CORE_DATA_DIR/app"
NODE_CORE_UPDATE_DIR="$NODE_CORE_DATA_DIR/runtime/update"
NODE_CORE_COMMIT_FILE="$NODE_CORE_DATA_DIR/runtime/node-core-commit"

require_user_installation() {
  if [[ "$(id -u)" == "0" ]]; then
    printf 'Refusing to update Node Core OS as root. Run the updater as your normal user without sudo.\n' >&2
    exit 1
  fi
  local home_real target_real uid
  [[ -n "${HOME:-}" && -d "$HOME" ]] || {
    printf 'A valid user HOME directory is required.\n' >&2
    exit 1
  }
  home_real="$(realpath -m -- "$HOME")"
  target_real="$(realpath -m -- "$NODE_CORE_DATA_DIR")"
  [[ "$target_real" == "$home_real/"* && "$target_real" != "$home_real" ]] || {
    printf 'Unsafe update path: NODE_CORE_DATA_DIR must be inside the current user HOME.\n' >&2
    exit 1
  }
  if [[ -e "$NODE_CORE_DATA_DIR" || -L "$NODE_CORE_DATA_DIR" ]]; then
    [[ ! -L "$NODE_CORE_DATA_DIR" && -d "$NODE_CORE_DATA_DIR" ]] || {
      printf 'Unsafe update path: installation must be a real directory, not a symbolic link.\n' >&2
      exit 1
    }
    uid="$(id -u)"
    [[ "$(stat -c '%u' "$NODE_CORE_DATA_DIR")" == "$uid" ]] || {
      printf 'Unsafe update path: installation is not owned by the current user.\n' >&2
      exit 1
    }
  fi
}

download_file() {
  local url="$1" destination="$2"
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error \
      --connect-timeout 15 --retry 3 --retry-delay 2 --retry-all-errors \
      --output "$destination" "$url"
  else
    wget --quiet --connect-timeout=15 --tries=4 --waitretry=2 \
      --output-document="$destination" "$url"
  fi
}

resolve_kubo_executable() {
  if [[ -n "${TERMUX_VERSION:-}" && -n "${PREFIX:-}" && -x "$PREFIX/bin/ipfs" ]]; then
    printf '%s\n' "$PREFIX/bin/ipfs"
    return 0
  fi
  printf '%s\n' "$NODE_CORE_DATA_DIR/bin/ipfs"
}

require_installation() {
  [[ -d "$NODE_CORE_APP_DIR" ]] || {
    printf 'Node Core OS installation not found: %s\n' "$NODE_CORE_DATA_DIR" >&2
    exit 1
  }
  local executable
  executable="$(resolve_kubo_executable)"
  [[ -x "$executable" ]] || {
    printf 'Kubo/IPFS executable not found: %s\n' "$executable" >&2
    printf 'Aborting update to protect the installation.\n' >&2
    exit 1
  }
  [[ -d "$NODE_CORE_DATA_DIR/ipfs" ]] || {
    printf 'Kubo repository not found. Aborting update to protect the installation.\n' >&2
    exit 1
  }
  [[ -d "$NODE_CORE_DATA_DIR/storage" ]] || {
    printf 'Local storage not found. Aborting update to protect the installation.\n' >&2
    exit 1
  }
}

validate_installed_application_for_recovery() {
  [[ -f "$NODE_CORE_APP_DIR/main.py" ]] || return 1
  python3 -m compileall -q "$NODE_CORE_APP_DIR/main.py" "$NODE_CORE_APP_DIR/node_core" || return 1
  (
    cd "$NODE_CORE_APP_DIR"
    python3 -m unittest discover -s tests -v
  )
}


recover_stale_cleanup_if_safe() {
  local app_backup="$NODE_CORE_UPDATE_DIR/app-backup"
  local marker_backup="$NODE_CORE_UPDATE_DIR/commit-marker-backup"
  local marker_state="$NODE_CORE_UPDATE_DIR/commit-marker-state"
  local current_commit='' backup_commit='' archive_dir=''

  # A real application backup means rollback may still be needed. Never auto-clear it.
  if [[ -e "$app_backup" || -L "$app_backup" ]]; then
    return 0
  fi

  # No marker files means there is no stale-cleanup case to reconcile.
  if [[ ! -e "$marker_backup" && ! -e "$marker_state" ]]; then
    return 0
  fi

  # The markers must describe a complete previous update transaction.
  [[ -f "$marker_state" && ! -L "$marker_state" ]] || {
    printf 'Recovery markers are incomplete; manual inspection is required.\n' >&2
    return 1
  }

  case "$(cat "$marker_state")" in
    present)
      [[ -f "$marker_backup" && ! -L "$marker_backup" && -f "$NODE_CORE_COMMIT_FILE" ]] || {
        printf 'Recovery commit markers are incomplete; refusing automatic recovery.\n' >&2
        return 1
      }
      backup_commit="$(cat "$marker_backup")"
      current_commit="$(cat "$NODE_CORE_COMMIT_FILE")"
      [[ "$backup_commit" =~ ^[0-9a-fA-F]{40}$ && "$current_commit" =~ ^[0-9a-fA-F]{40}$ ]] || {
        printf 'Recovery commit markers are invalid; refusing automatic recovery.\n' >&2
        return 1
      }
      ;;
    absent)
      [[ ! -e "$marker_backup" && ! -e "$NODE_CORE_COMMIT_FILE" ]] || {
        printf 'Recovery marker state conflicts with the current commit marker.\n' >&2
        return 1
      }
      ;;
    *)
      printf 'Recovery marker state is unknown; manual inspection is required.\n' >&2
      return 1
      ;;
  esac

  printf 'Found recovery markers without an application backup.\n'
  require_installation
  printf 'Checking the installed application before reconciling interrupted cleanup.\n'
  if ! validate_installed_application_for_recovery; then
    printf 'Installed application validation failed; recovery files were preserved.\n' >&2
    return 1
  fi

  archive_dir="$(mktemp -d "$NODE_CORE_DATA_DIR/runtime/update-recovery-XXXXXX")" || {
    printf 'Could not create a recovery archive; recovery files were preserved.\n' >&2
    return 1
  }

  if [[ -f "$marker_backup" ]]; then
    cp "$marker_backup" "$archive_dir/commit-marker-backup" || return 1
  fi
  cp "$marker_state" "$archive_dir/commit-marker-state" || return 1

  if [[ -f "$marker_backup" ]]; then
    cmp -s "$marker_backup" "$archive_dir/commit-marker-backup" || {
      printf 'Recovery marker archive verification failed; original files were preserved.\n' >&2
      return 1
    }
  fi
  cmp -s "$marker_state" "$archive_dir/commit-marker-state" || {
    printf 'Recovery state archive verification failed; original files were preserved.\n' >&2
    return 1
  }

  cat > "$archive_dir/RECOVERY.txt" <<EOF
Node Core OS updater recovery marker archive.
Created after validating the installed Node Core OS and P2P Contracts application.
No application backup existed, so automatic rollback was not possible.
Original marker files were copied and verified before their active copies were removed.
Current commit: ${current_commit:-absent}
Previous commit: ${backup_commit:-absent}
EOF

  rm -f "$marker_backup" "$marker_state" || {
    printf 'Could not clear active recovery markers; archived copies remain at %s\n' "$archive_dir" >&2
    return 1
  }

  printf '✓ Installed application validation passed.\n'
  printf '✓ Recovery markers archived at: %s\n' "$archive_dir"
  printf '✓ The updater can continue without deleting the recovery evidence.\n'
}

require_no_pending_recovery() {
  local app_backup="$NODE_CORE_UPDATE_DIR/app-backup"
  local marker_backup="$NODE_CORE_UPDATE_DIR/commit-marker-backup"
  local marker_state="$NODE_CORE_UPDATE_DIR/commit-marker-state"

  if [[ -e "$app_backup" || -e "$marker_backup" || -e "$marker_state" ]]; then
    printf 'A previous update left recovery files that require inspection.\n' >&2
    printf 'Refusing to start another update to protect the existing recovery data.\n' >&2
    printf 'Recovery directory: %s\n' "$NODE_CORE_UPDATE_DIR" >&2
    printf 'Do not delete these files until the installed application and commit marker have been verified.\n' >&2
    exit 1
  fi
}

ensure_python_environment() {
  local requirements_file="$NODE_CORE_APP_DIR/requirements.txt"
  local python_environment="$NODE_CORE_DATA_DIR/runtime/node-core-venv"
  mkdir -p "$NODE_CORE_DATA_DIR/runtime"
  if [[ ! -x "$python_environment/bin/python" ]]; then
    python3 -m venv "$python_environment" || {
      printf 'Could not create the private Python environment. Install python3-venv and retry.\n' >&2
      return 1
    }
  fi
  if [[ ! -f "$requirements_file" ]]; then
    printf 'No requirements.txt in the current installation; preserving compatibility until the update archive is installed.\n'
    return 0
  fi
  if grep -Eq '^[[:space:]]*[^#[:space:]]' "$requirements_file"; then
    "$python_environment/bin/python" -m pip install --disable-pip-version-check --upgrade -r "$requirements_file" || {
      printf 'Could not install Node Core OS Python dependencies.\n' >&2
      return 1
    }
  fi
  if grep -Eiq '^[[:space:]]*cryptography([<=>!~[:space:]]|$)' "$requirements_file"; then
    "$python_environment/bin/python" -c 'import cryptography; print("Verified cryptography:", cryptography.__version__)' || return 1
  fi
}

ensure_launchers() {
  mkdir -p "$NODE_CORE_DATA_DIR/bin"

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

  # Remove only the legacy launcher generated by the bundled-app installer.
  local legacy_hashpaper_launcher="$NODE_CORE_DATA_DIR/bin/hashpaper"
  if [[ -f "$legacy_hashpaper_launcher" && ! -L "$legacy_hashpaper_launcher" ]] && \
    grep -Fq '/app/applications/hashpaper/main.py' "$legacy_hashpaper_launcher"; then
    rm -f -- "$legacy_hashpaper_launcher"
  fi

  cat > "$NODE_CORE_DATA_DIR/bin/node-core-kubo-daemon" <<EOF
#!/usr/bin/env bash
set -euo pipefail
ipfs="$NODE_CORE_DATA_DIR/bin/ipfs"
if "\$ipfs" daemon --help 2>&1 | grep -q -- '--enable-pubsub-experiment'; then
  exec "\$ipfs" daemon --enable-pubsub-experiment
fi
exec "\$ipfs" daemon
EOF
  chmod 700 "$NODE_CORE_DATA_DIR/bin/node-core-kubo-daemon"

}

refresh_kubo_service_unit_if_present() {
  local unit_path="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/node-core-kubo.service"
  [[ -f "$unit_path" ]] || return 0
  [[ -f "$NODE_CORE_APP_DIR/installer/lib/service.sh" ]] || return 0
  # Refresh only the Node Core-managed user unit. Do not restart a running Kubo daemon.
  source "$NODE_CORE_APP_DIR/installer/lib/service.sh"
  write_kubo_service_unit
  if command -v systemctl >/dev/null 2>&1 && systemctl --user daemon-reload >/dev/null 2>&1; then
    printf 'Updated the Node Core Kubo service launcher. Restart Kubo from Node Core OS to activate PubSub support.\n'
  else
    printf 'Updated the Kubo service launcher, but user systemd could not reload it.\n' >&2
  fi
}

migrate_termux_config() {
  local config="$NODE_CORE_DATA_DIR/config.json"
  local executable
  executable="$(resolve_kubo_executable)"
  [[ -n "${TERMUX_VERSION:-}" && -x "$executable" && -f "$config" ]] || return 0

  if ! "$executable" version >/dev/null 2>&1; then
    printf 'Termux Kubo executable failed verification: %s\n' "$executable" >&2
    return 1
  fi

  python3 - "$config" "$executable" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
executable = sys.argv[2]
data = json.loads(path.read_text(encoding="utf-8"))
if data.get("ipfs_executable") != executable:
    data["ipfs_executable"] = executable
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

latest_commit() {
  # A downloaded release package may carry its exact source snapshot. Prefer it
  # over the network so the complete update package is independently usable.
  local package_dir package_commit
  package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$package_dir/source-package.tar.gz" && -f "$package_dir/SOURCE_COMMIT" ]]; then
    package_commit="$(tr -d '\\r\\n' < "$package_dir/SOURCE_COMMIT")"
    if [[ "$package_commit" =~ ^[0-9a-fA-F]{40}$ ]] &&
       tar -tzf "$package_dir/source-package.tar.gz" >/dev/null 2>&1; then
      printf '%s\\n' "${package_commit,,}"
      return 0
    fi
    printf 'Bundled update source or commit marker is invalid; refusing package update.\\n' >&2
    return 1
  fi

  local response="$NODE_CORE_UPDATE_DIR/latest-commit.json"
  local temporary_response encoded_branch commit url downloaded=0
  mkdir -p "$NODE_CORE_UPDATE_DIR"

  # A slash is valid in a query parameter. Keep the ref readable so GitHub's
  # API can resolve branch names containing slashes without path ambiguity.
  encoded_branch="$NODE_CORE_BRANCH"

  temporary_response="$(mktemp "$NODE_CORE_UPDATE_DIR/latest-commit.XXXXXX")" || {
    printf 'Could not create a temporary update metadata file.\n' >&2
    return 1
  }

  # The query endpoint accepts a branch ref with slashes. For the path
  # endpoint, encode slashes so the branch remains a single URL component.
  local encoded_path_ref
  encoded_path_ref="$(python3 - "$NODE_CORE_BRANCH" <<'PY'
from urllib.parse import quote
import sys
print(quote(sys.argv[1], safe=""))
PY
  )" || {
    printf 'Could not encode the fallback update ref.\\n' >&2
    return 1
  }
  local urls=(
    "https://api.github.com/repos/byLAEV/Node-Core-OS/commits?sha=$encoded_branch&per_page=1"
    "https://api.github.com/repos/byLAEV/Node-Core-OS/commits/$encoded_path_ref"
  )
  for url in "${urls[@]}"; do
    rm -f -- "$temporary_response"
    printf 'Trying update metadata source: %s\n' "$url" >&2
    if download_file "$url" "$temporary_response"; then
      downloaded=1
      break
    fi
    printf 'Update metadata source failed; trying the next official source.\n' >&2
  done
  if [[ "$downloaded" != 1 ]]; then
    # GitHub REST API requests can be rate-limited for unauthenticated users.
    # Fall back to the public Git remote-ref protocol without requiring root.
    if command -v git >/dev/null 2>&1; then
      local remote_commit
      if remote_commit="$(git ls-remote "$NODE_CORE_REPOSITORY" "refs/heads/$NODE_CORE_BRANCH" 2>/dev/null | awk 'NR == 1 { print $1 }')" &&
         [[ "$remote_commit" =~ ^[0-9a-fA-F]{40}$ ]]; then
        rm -f -- "$temporary_response"
        printf '%s\n' "${remote_commit,,}"
        return 0
      fi
      printf 'Git remote-ref fallback failed.\n' >&2
    fi
    rm -f -- "$temporary_response"
    printf 'Could not retrieve update metadata from any official GitHub source.\n' >&2
    return 1
  fi

  if ! commit="$(python3 - "$temporary_response" <<'PY'
import json
import re
import sys
from pathlib import Path

try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"GitHub update metadata is unreadable: {exc}")

# /commits?sha=... returns a list; /commits/{ref} returns one object.
if isinstance(data, list):
    if not data:
        raise SystemExit("GitHub returned no commits for the requested branch.")
    data = data[0]
commit = data.get("sha") if isinstance(data, dict) else None
if not isinstance(commit, str) or re.fullmatch(r"[0-9a-fA-F]{40}", commit) is None:
    raise SystemExit("GitHub returned invalid commit metadata; refusing to update.")
print(commit.lower())
PY
  )"; then
    rm -f -- "$temporary_response"
    printf 'GitHub returned invalid update metadata; refusing to update.\n' >&2
    return 1
  fi

  mv -f -- "$temporary_response" "$response" || {
    rm -f -- "$temporary_response"
    printf 'Could not save validated update metadata.\n' >&2
    return 1
  }
  printf '%s\n' "$commit"
}

backup_app() {
  local backup="$NODE_CORE_UPDATE_DIR/app-backup"
  rm -rf "$backup"
  cp -R "$NODE_CORE_APP_DIR" "$backup"
  printf '%s\n' "$backup"
}

update_application() (
  set -euo pipefail
  local commit="$1"
  local archive="$NODE_CORE_UPDATE_DIR/source.tar.gz"
  local extract="$NODE_CORE_UPDATE_DIR/source"

  rm -rf "$extract" || return 1
  mkdir -p "$extract" || return 1
  local source_url downloaded=0
  local package_dir
  package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$package_dir/source-package.tar.gz" ]]; then
    cp "$package_dir/source-package.tar.gz" "$archive" || return 1
    tar -tzf "$archive" >/dev/null 2>&1 || {
      printf 'Bundled update source archive is invalid.\\n' >&2
      return 1
    }
    downloaded=1
  else
    local archive_urls=(
      "https://github.com/byLAEV/Node-Core-OS/archive/$commit.tar.gz"
      "https://codeload.github.com/byLAEV/Node-Core-OS/tar.gz/$commit"
    )
    for source_url in "${archive_urls[@]}"; do
      rm -f -- "$archive"
      printf 'Trying Node Core OS source archive: %s\\n' "$source_url" >&2
      if download_file "$source_url" "$archive"; then
        if tar -tzf "$archive" >/dev/null 2>&1; then
          downloaded=1
          break
        fi
        printf 'Downloaded archive is invalid; trying the next official GitHub source.\\n' >&2
      else
        printf 'Source archive download failed; trying the next official GitHub source.\\n' >&2
      fi
    done
  fi
  [[ "$downloaded" == 1 ]] || {
    rm -f -- "$archive"
    printf 'Could not obtain a valid Node Core OS source archive.\\n' >&2
    return 1
  }
  tar -xzf "$archive" -C "$extract" || return 1

  local source
  source="$(find "$extract" -mindepth 1 -maxdepth 1 -type d -print -quit)"
  [[ -n "$source" ]] || {
    printf 'Update archive did not contain the Node Core OS source.\n' >&2
    return 1
  }

  rm -rf "$NODE_CORE_APP_DIR" || return 1
  mkdir -p "$NODE_CORE_APP_DIR" || return 1
  cp -R "$source"/. "$NODE_CORE_APP_DIR"/ || return 1
  rm -rf "$NODE_CORE_APP_DIR/.git" || return 1
  # HashPaper is a separate application and is not part of Node Core OS 1.4.0.
  rm -rf "$NODE_CORE_APP_DIR/applications/hashpaper" "$NODE_CORE_APP_DIR/applications/p2p_contracts" || return 1
  rm -f "$NODE_CORE_APP_DIR/installer/hashpaper-install.sh" "$NODE_CORE_APP_DIR/installer/hashpaper-update.sh"
  rm -f "$NODE_CORE_APP_DIR/installer/opentimestamps-server-install.sh"
  rm -f "$NODE_CORE_APP_DIR/installer/tests/hashpaper-install.sh" "$NODE_CORE_APP_DIR/installer/tests/hashpaper-update.sh"
  rm -f "$NODE_CORE_APP_DIR/docs/HASHPAPER.md" "$NODE_CORE_APP_DIR/docs/HASHPAPER-FUNCTIONAL-MANIFEST.md"
  rm -f "$NODE_CORE_APP_DIR/tests/test_hashpaper_storage_layout.py"
  rm -f "$NODE_CORE_APP_DIR/.github/workflows/hashpaper-opentimestamps-live.yml" "$NODE_CORE_APP_DIR/.github/workflows/hashpaper-python-matrix.yml"
  rm -f "$NODE_CORE_APP_DIR/docs/P2P-CONTRACTS-APPLICATION-STRUCTURE.md" \
    "$NODE_CORE_APP_DIR/docs/P2P-CONTRACTS-BTC-REQUEST-PROTOTYPE.md" \
    "$NODE_CORE_APP_DIR/docs/P2P-CONTRACTS-DEVELOPMENT-PLAN.md" \
    "$NODE_CORE_APP_DIR/docs/P2P-CONTRACTS-PUBLIC-MANIFEST-PROTOCOL.md" \
    "$NODE_CORE_APP_DIR/docs/P2P-CONTRACTS-SCHEMAS.md" \
    "$NODE_CORE_APP_DIR/docs/P2P-CONTRACTS-TECHNICAL-AUDIT.md"
  rm -f "$NODE_CORE_APP_DIR/.github/workflows/three-independent-ubuntu-p2p-contracts.yml" \
    "$NODE_CORE_APP_DIR/.github/workflows/three-independent-ubuntu-p2p-e2e.yml"

  [[ -f "$NODE_CORE_APP_DIR/requirements.txt" ]] || {
    printf 'Update is missing requirements.txt; refusing activation.\n' >&2
    return 1
  }
  ensure_python_environment || return 1
  local python_environment="$NODE_CORE_DATA_DIR/runtime/node-core-venv"

  # P2P Contracts is suspended and removed from the installed runtime.
  python3 - "$NODE_CORE_APP_DIR/VERSION" <<'PY'
import re
import sys
from pathlib import Path
path = Path(sys.argv[1])
version = path.read_text(encoding="utf-8").strip()
if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
    raise SystemExit(f"Invalid Node Core OS version in {path}: {version!r}")
print("Node Core OS version:", version)
PY
  python3 -m compileall -q "$NODE_CORE_APP_DIR/main.py" "$NODE_CORE_APP_DIR/node_core" || return 1
  (cd "$NODE_CORE_APP_DIR" && "$python_environment/bin/python" -m unittest discover -s tests -v) || return 1
  printf '✓ Node Core OS core tests validated.\n'
)

backup_commit_marker() {
  local backup="$NODE_CORE_UPDATE_DIR/commit-marker-backup"
  if [[ -f "$NODE_CORE_COMMIT_FILE" ]]; then
    cp "$NODE_CORE_COMMIT_FILE" "$backup" || return 1
    printf 'present\n' > "$NODE_CORE_UPDATE_DIR/commit-marker-state" || return 1
  else
    rm -f "$backup" || return 1
    printf 'absent\n' > "$NODE_CORE_UPDATE_DIR/commit-marker-state" || return 1
  fi
}

write_commit_marker() {
  local commit="$1"
  local temporary_marker
  temporary_marker="$(mktemp "$NODE_CORE_DATA_DIR/runtime/node-core-commit.XXXXXX")" || {
    printf 'Could not create a temporary commit marker.\n' >&2
    return 1
  }
  if ! printf '%s\n' "$commit" > "$temporary_marker" ||
     ! mv -f -- "$temporary_marker" "$NODE_CORE_COMMIT_FILE"; then
    rm -f -- "$temporary_marker"
    printf 'Could not activate the new commit marker.\n' >&2
    return 1
  fi
}

rollback_application() {
  local backup="$NODE_CORE_UPDATE_DIR/app-backup"
  local marker_backup="$NODE_CORE_UPDATE_DIR/commit-marker-backup"
  [[ -d "$backup" ]] || return 1
  rm -rf "$NODE_CORE_APP_DIR" || return 1
  cp -R "$backup" "$NODE_CORE_APP_DIR" || return 1

  case "$(cat "$NODE_CORE_UPDATE_DIR/commit-marker-state" 2>/dev/null || true)" in
    present)
      [[ -f "$marker_backup" ]] || return 1
      cp "$marker_backup" "$NODE_CORE_COMMIT_FILE" || return 1
      ;;
    absent)
      rm -f "$NODE_CORE_COMMIT_FILE" || return 1
      ;;
    *)
      printf 'Cannot determine prior commit marker state; manual recovery may be required.\n' >&2
      return 1
      ;;
  esac
}

cleanup_update_files() {
  rm -rf "$NODE_CORE_UPDATE_DIR/source" "$NODE_CORE_UPDATE_DIR/app-backup"
  rm -f "$NODE_CORE_UPDATE_DIR/source.tar.gz" "$NODE_CORE_UPDATE_DIR/latest-commit.json"
  rm -f "$NODE_CORE_UPDATE_DIR/commit-marker-backup" "$NODE_CORE_UPDATE_DIR/commit-marker-state"
}

main() {
  printf '%s\n' 'Node Core OS updater'
  printf '%s\n' 'byLAEV'
  printf '\n'
  require_user_installation
  recover_stale_cleanup_if_safe
  require_no_pending_recovery
  require_installation
  migrate_termux_config
  ensure_python_environment
  ensure_launchers
  refresh_kubo_service_unit_if_present

  local remote_commit local_commit
  remote_commit="$(latest_commit)"
  local_commit=''

  if [[ -f "$NODE_CORE_COMMIT_FILE" ]]; then
    local_commit="$(cat "$NODE_CORE_COMMIT_FILE")"
  fi

  printf 'Installed Node Core commit: %s\n' "${local_commit:-unknown}"
  printf 'Available Node Core commit: %s\n' "$remote_commit"
  printf '\n'

  if [[ -n "$local_commit" && "$local_commit" == "$remote_commit" ]]; then
    printf 'Node Core OS is already up to date.\n'
    cleanup_update_files
    return 0
  fi

  printf '%s\n' 'An application update is available.'
  printf '%s\n' 'The updater will modify only the Node Core application.'
  printf '%s\n' 'Kubo/IPFS binary, IPFS repository, and local storage will not be replaced.'
  printf '%s\n' 'On Termux, config.json may be migrated only to point Node Core to the existing Android-compatible Kubo executable.'
  printf '\n'
  read -r -p 'Update Node Core OS? [Y/n] ' answer
  case "${answer:-y}" in
    y|Y|yes|YES) ;;
    *) printf 'Update cancelled.\n'; cleanup_update_files; return 0 ;;
  esac

  local backup
  backup="$(backup_app)"
  if ! backup_commit_marker; then
    printf 'Failed to back up the installed commit marker; update cancelled.\n' >&2
    rm -rf "$NODE_CORE_UPDATE_DIR/app-backup"
    cleanup_update_files
    return 1
  fi

  if update_application "$remote_commit" && write_commit_marker "$remote_commit"; then
    printf '\n✓ Node Core application updated.\n'
    printf '✓ Kubo/IPFS binary preserved.\n'
    printf '✓ Kubo repository preserved.\n'
    printf '✓ Local storage preserved.\n'
    printf '✓ Configuration preserved unless Termux executable path migration was required.\n'
    cleanup_update_files
  else
    printf '\nUpdate verification failed. Rolling back Node Core application...\n' >&2
    if rollback_application; then
      printf '✓ Node Core application and commit marker restored.\n' >&2
      printf 'Kubo/IPFS and persistent data were not modified.\n' >&2
      cleanup_update_files
    else
      printf 'ERROR: Node Core application rollback failed.\n' >&2
      printf 'Recovery files were retained for manual recovery: %s\n' "$NODE_CORE_UPDATE_DIR" >&2
      printf 'Do not delete the recovery directory until the previous application and commit marker have been restored.\n' >&2
    fi
    exit 1
  fi
}

main "$@"
