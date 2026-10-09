#!/usr/bin/env bash
set -euo pipefail

# Transactional application deployment primitive.
# It only replaces app/ and the application commit marker. It never touches
# Kubo, the IPFS repository, local storage, or config.json.
node_core_apply_application() {
  local source_dir="${1:-}" commit="${2:-}"
  local data_dir="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
  local app_dir="$data_dir/app"
  local runtime_dir="$data_dir/runtime"
  local update_dir="$runtime_dir/update"
  local stage_dir="$update_dir/app-stage"
  local backup_dir="$runtime_dir/backups"
  local backup_app=""
  local old_commit_file="$runtime_dir/node-core-commit"
  local staged_commit="$update_dir/node-core-commit.new"
  local had_old_app=0
  local had_old_commit=0

  if [[ "$(id -u)" == "0" ]]; then
    printf 'Refusing to apply an application update as root.\n' >&2
    return 1
  fi
  [[ -n "$source_dir" && -n "$commit" ]] || {
    printf 'Usage: node_core_apply_application SOURCE_DIRECTORY COMMIT_ID\n' >&2
    return 1
  }
  [[ -d "$data_dir" && ! -L "$data_dir" ]] || {
    printf 'Node Core OS data directory must exist and must not be a symbolic link.\n' >&2
    return 1
  }
  [[ "$(stat -c '%u' "$data_dir")" == "$(id -u)" ]] || {
    printf 'Node Core OS data directory is not owned by the current user.\n' >&2
    return 1
  }

  local home_real data_real source_real
  home_real="$(realpath -m -- "$HOME")"
  data_real="$(realpath -m -- "$data_dir")"
  source_real="$(realpath -e -- "$source_dir")"
  [[ "$data_real" == "$home_real/"* && "$data_real" != "$home_real" ]] || {
    printf 'Unsafe application path: data directory must be inside HOME.\n' >&2
    return 1
  }
  [[ -d "$source_real" && ! -L "$source_dir" ]] || {
    printf 'Application source must be a real directory.\n' >&2
    return 1
  }
  [[ -f "$source_real/main.py" && -d "$source_real/node_core" ]] || {
    printf 'Application source is incomplete (main.py and node_core/ are required).\n' >&2
    return 1
  }
  [[ ! -L "$app_dir" ]] || {
    printf 'Refusing to replace app/: it is a symbolic link.\n' >&2
    return 1
  }
  [[ ! -e "$old_commit_file" || ( -f "$old_commit_file" && ! -L "$old_commit_file" ) ]] || {
    printf 'Refusing to replace an unsafe application commit marker.\n' >&2
    return 1
  }

  for directory in "$runtime_dir" "$update_dir" "$backup_dir"; do
    [[ ! -L "$directory" ]] || {
      printf 'Refusing to use a symbolic-link runtime/update/backup directory: %s\n' "$directory" >&2
      return 1
    }
  done
  mkdir -p "$runtime_dir" "$update_dir" "$backup_dir"
  rm -rf -- "$stage_dir"
  mkdir -m 700 "$stage_dir"
  if ! cp -R "$source_real"/. "$stage_dir"/; then
    rm -rf -- "$stage_dir"
    printf 'Unable to stage the application source.\n' >&2
    return 1
  fi
  rm -rf -- "$stage_dir/.git"
  if ! python3 -m compileall -q "$stage_dir/main.py" "$stage_dir/node_core"; then
    rm -rf -- "$stage_dir"
    printf 'Staged application failed Python compilation; current application was not changed.\n' >&2
    return 1
  fi

  # Keep the backup instead of deleting it automatically; recovery is explicit.
  backup_app="$backup_dir/app-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  if [[ -e "$app_dir" ]]; then
    [[ -d "$app_dir" && ! -L "$app_dir" ]] || {
      rm -rf -- "$stage_dir"
      printf 'Refusing to replace app/: existing path is not a real directory.\n' >&2
      return 1
    }
    if ! cp -R "$app_dir" "$backup_app"; then
      rm -rf -- "$stage_dir"
      printf 'Unable to back up current application; no changes applied.\n' >&2
      return 1
    fi
    had_old_app=1
  fi

  if [[ -f "$old_commit_file" ]]; then
    had_old_commit=1
  fi

  if [[ "$had_old_app" == "1" ]]; then
    if ! mv -- "$app_dir" "$update_dir/app-previous"; then
      rm -rf -- "$stage_dir"
      printf 'Unable to move current application to transaction staging.\n' >&2
      return 1
    fi
  fi

  if ! mv -- "$stage_dir" "$app_dir"; then
    if [[ "$had_old_app" == "1" && -d "$update_dir/app-previous" ]]; then
      mv -- "$update_dir/app-previous" "$app_dir" || {
        printf 'CRITICAL: application move failed and automatic restoration failed. Backup: %s\n' "$backup_app" >&2
        return 1
      }
    fi
    rm -rf -- "$stage_dir"
    printf 'Unable to activate staged application.\n' >&2
    return 1
  fi

  printf '%s\n' "$commit" > "$staged_commit"
  chmod 600 "$staged_commit"
  if ! mv -f -- "$staged_commit" "$old_commit_file"; then
    rm -rf -- "$app_dir"
    if [[ "$had_old_app" == "1" && -d "$update_dir/app-previous" ]]; then
      mv -- "$update_dir/app-previous" "$app_dir" || {
        printf 'CRITICAL: commit marker update failed and application restoration failed. Backup: %s\n' "$backup_app" >&2
        return 1
      }
    fi
    if [[ "$had_old_commit" != "1" ]]; then
      rm -f -- "$old_commit_file"
    fi
    printf 'Unable to record application commit; prior application restored.\n' >&2
    return 1
  fi

  rm -rf -- "$update_dir/app-previous"
  printf 'Application deployed and compiled successfully.\n'
  printf 'Installed commit: %s\n' "$commit"
  if [[ "$had_old_app" == "1" ]]; then
    printf 'Recovery backup retained at: %s\n' "$backup_app"
  fi
}
