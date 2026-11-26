#!/usr/bin/env bash
set -euo pipefail

# Transactional application deployment primitive.
# It only replaces app/ and the application commit marker. It never touches
# Kubo, the IPFS repository, local storage, or config.json.
node_core_apply_application() (
  local source_dir="${1:-}" commit="${2:-}"
  local data_dir="${NODE_CORE_DATA_DIR:-$HOME/.node-core}"
  local app_dir="$data_dir/app"
  local runtime_dir="$data_dir/runtime"
  local update_dir="$runtime_dir/update"
  local backup_dir="$runtime_dir/backups"
  local old_commit_file="$runtime_dir/node-core-commit"
  local home_real data_real source_real uid directory resolved
  local transaction_dir="" stage_dir="" previous_app="" staged_commit=""
  local previous_commit="" restore_commit="" backup_app=""
  local had_old_app=0 had_old_commit=0

  if [[ "$(id -u)" == "0" ]]; then
    printf 'Refusing to apply an application update as root.\n' >&2
    return 1
  fi
  [[ -n "$source_dir" && -n "$commit" ]] || {
    printf 'Usage: node_core_apply_application SOURCE_DIRECTORY COMMIT_ID\n' >&2
    return 1
  }
  [[ "$commit" != *$'\n'* && "$commit" != *$'\r'* ]] || {
    printf 'Commit identifier must be a non-empty single line.\n' >&2
    return 1
  }
  [[ -n "${HOME:-}" && -d "$HOME" ]] || {
    printf 'A valid user HOME directory is required.\n' >&2
    return 1
  }
  [[ -d "$data_dir" && ! -L "$data_dir" ]] || {
    printf 'Node Core OS data directory must exist and must not be a symbolic link.\n' >&2
    return 1
  }

  uid="$(id -u)"
  [[ "$(stat -c '%u' "$data_dir")" == "$uid" ]] || {
    printf 'Node Core OS data directory is not owned by the current user.\n' >&2
    return 1
  }

  home_real="$(realpath -e -- "$HOME")"
  data_real="$(realpath -e -- "$data_dir")"
  [[ "$data_real" == "$home_real/"* && "$data_real" != "$home_real" ]] || {
    printf 'Unsafe application path: data directory must be inside HOME.\n' >&2
    return 1
  }
  [[ ! -L "$source_dir" ]] || {
    printf 'Application source must not be a symbolic link.\n' >&2
    return 1
  }
  if ! source_real="$(realpath -e -- "$source_dir")"; then
    printf 'Application source directory does not exist.\n' >&2
    return 1
  fi
  [[ -d "$source_real" && -f "$source_real/main.py" && -d "$source_real/node_core" ]] || {
    printf 'Application source is incomplete (main.py and node_core/ are required).\n' >&2
    return 1
  }

  # Validate every persistent path before creating or replacing anything.
  if [[ -e "$app_dir" || -L "$app_dir" ]]; then
    [[ -d "$app_dir" && ! -L "$app_dir" ]] || {
      printf 'Refusing to replace app/: existing path is not a real directory.\n' >&2
      return 1
    }
    [[ "$(stat -c '%u' "$app_dir")" == "$uid" ]] || {
      printf 'Refusing to replace app/: directory is not owned by the current user.\n' >&2
      return 1
    }
  fi
  if [[ -e "$old_commit_file" || -L "$old_commit_file" ]]; then
    [[ -f "$old_commit_file" && ! -L "$old_commit_file" ]] || {
      printf 'Refusing to replace an unsafe application commit marker.\n' >&2
      return 1
    }
    [[ "$(stat -c '%u' "$old_commit_file")" == "$uid" ]] || {
      printf 'Refusing to replace an application commit marker not owned by the current user.\n' >&2
      return 1
    }
  fi

  for directory in "$runtime_dir" "$update_dir" "$backup_dir"; do
    if [[ -e "$directory" || -L "$directory" ]]; then
      [[ -d "$directory" && ! -L "$directory" ]] || {
        printf 'Refusing to use a path that is not a real directory: %s\n' "$directory" >&2
        return 1
      }
      [[ "$(stat -c '%u' "$directory")" == "$uid" ]] || {
        printf 'Refusing to use a directory not owned by the current user: %s\n' "$directory" >&2
        return 1
      }
      resolved="$(realpath -e -- "$directory")"
      [[ "$resolved" == "$data_real/"* ]] || {
        printf 'Refusing to use a directory outside the Node Core OS data directory: %s\n' "$directory" >&2
        return 1
      }
    fi
  done

  umask 077
  if ! mkdir -p -- "$runtime_dir" "$update_dir" "$backup_dir"; then
    printf 'Unable to prepare private application update directories.\n' >&2
    return 1
  fi
  # Recheck after mkdir so existing non-directory or redirected paths fail closed.
  for directory in "$runtime_dir" "$update_dir" "$backup_dir"; do
    [[ -d "$directory" && ! -L "$directory" ]] || {
      printf 'Unsafe application update directory: %s\n' "$directory" >&2
      return 1
    }
    [[ "$(stat -c '%u' "$directory")" == "$uid" ]] || {
      printf 'Application update directory is not owned by the current user: %s\n' "$directory" >&2
      return 1
    }
  done

  # Never delete or reuse a fixed staging path: interrupted runs may contain
  # the only recoverable copy of the previous application.
  if ! transaction_dir="$(mktemp -d -- "$update_dir/transaction.XXXXXXXX")"; then
    printf 'Unable to create a unique application transaction directory.\n' >&2
    return 1
  fi
  stage_dir="$transaction_dir/app-stage"
  previous_app="$transaction_dir/app-previous"
  staged_commit="$transaction_dir/node-core-commit.new"
  previous_commit="$transaction_dir/node-core-commit.previous"
  restore_commit="$transaction_dir/node-core-commit.restore"

  if ! mkdir -m 700 -- "$stage_dir"; then
    rm -rf -- "$transaction_dir"
    printf 'Unable to create application staging directory.\n' >&2
    return 1
  fi
  if ! cp -R -- "$source_real"/. "$stage_dir"/; then
    rm -rf -- "$transaction_dir"
    printf 'Unable to stage the application source.\n' >&2
    return 1
  fi
  if ! rm -rf -- "$stage_dir/.git"; then
    rm -rf -- "$transaction_dir"
    printf 'Unable to remove Git metadata from the staged application.\n' >&2
    return 1
  fi
  if ! python3 -m compileall -q "$stage_dir/main.py" "$stage_dir/node_core"; then
    rm -rf -- "$transaction_dir"
    printf 'Staged application failed Python compilation; current application was not changed.\n' >&2
    return 1
  fi

  # Prepare every piece of transaction metadata before the active application moves.
  if ! printf '%s\n' "$commit" > "$staged_commit" || ! chmod 600 -- "$staged_commit"; then
    rm -rf -- "$transaction_dir"
    printf 'Unable to prepare the staged application commit marker.\n' >&2
    return 1
  fi
  if [[ -f "$old_commit_file" ]]; then
    if ! cp -p -- "$old_commit_file" "$previous_commit"; then
      rm -rf -- "$transaction_dir"
      printf 'Unable to preserve the current application commit marker.\n' >&2
      return 1
    fi
    had_old_commit=1
  fi

  if [[ -d "$app_dir" ]]; then
    if ! backup_app="$(mktemp -d -- "$backup_dir/app-XXXXXXXX")"; then
      rm -rf -- "$transaction_dir"
      printf 'Unable to create an application recovery backup directory.\n' >&2
      return 1
    fi
    if ! cp -R -- "$app_dir"/. "$backup_app"/; then
      rm -rf -- "$backup_app" "$transaction_dir"
      printf 'Unable to back up current application; no changes applied.\n' >&2
      return 1
    fi
    chmod 700 -- "$backup_app"
    had_old_app=1
  fi

  if [[ "$had_old_app" == "1" ]]; then
    if ! mv -- "$app_dir" "$previous_app"; then
      # A failed rename must not silently strand the live application.
      if [[ ! -e "$app_dir" && -d "$previous_app" ]]; then
        if ! mv -- "$previous_app" "$app_dir"; then
          printf 'CRITICAL: unable to restore the application after a failed staging rename. Transaction: %s; backup: %s\n' "$transaction_dir" "$backup_app" >&2
          return 1
        fi
      fi
      rm -rf -- "$transaction_dir"
      printf 'Unable to move the current application into transaction staging.\n' >&2
      return 1
    fi
  fi

  if ! mv -- "$stage_dir" "$app_dir"; then
    if [[ "$had_old_app" == "1" && ! -e "$app_dir" && -d "$previous_app" ]]; then
      if ! mv -- "$previous_app" "$app_dir"; then
        printf 'CRITICAL: application activation failed and automatic restoration failed. Transaction: %s; backup: %s\n' "$transaction_dir" "$backup_app" >&2
        return 1
      fi
    elif [[ "$had_old_app" == "1" ]]; then
      printf 'CRITICAL: application activation failed and the previous application is retained at %s. Backup: %s\n' "$previous_app" "$backup_app" >&2
      return 1
    fi
    rm -rf -- "$transaction_dir"
    printf 'Unable to activate staged application.\n' >&2
    return 1
  fi

  # If recording the version fails, restore the previous app and previous marker.
  if ! mv -f -- "$staged_commit" "$old_commit_file"; then
    local recovery_failed=0
    if [[ -d "$app_dir" && ! -L "$app_dir" ]]; then
      rm -rf -- "$app_dir" || recovery_failed=1
    else
      recovery_failed=1
    fi
    if [[ "$had_old_app" == "1" ]]; then
      if [[ ! -e "$app_dir" && -d "$previous_app" ]]; then
        mv -- "$previous_app" "$app_dir" || recovery_failed=1
      else
        recovery_failed=1
      fi
    fi
    if [[ "$had_old_commit" == "1" ]]; then
      if cp -p -- "$previous_commit" "$restore_commit" && mv -f -- "$restore_commit" "$old_commit_file"; then
        :
      else
        recovery_failed=1
      fi
    else
      rm -f -- "$old_commit_file" || recovery_failed=1
    fi
    if [[ "$recovery_failed" != "0" ]]; then
      printf 'CRITICAL: commit marker update failed and automatic restoration was incomplete. Transaction: %s; backup: %s\n' "$transaction_dir" "$backup_app" >&2
      return 1
    fi
    rm -rf -- "$transaction_dir"
    printf 'Unable to record application commit; prior application and marker restored.\n' >&2
    return 1
  fi

  if [[ ! -f "$app_dir/main.py" || ! -d "$app_dir/node_core" ]] || ! grep -Fqx -- "$commit" "$old_commit_file"; then
    local recovery_failed=0
    if [[ -d "$app_dir" && ! -L "$app_dir" ]]; then
      rm -rf -- "$app_dir" || recovery_failed=1
    else
      recovery_failed=1
    fi
    if [[ "$had_old_app" == "1" ]]; then
      if [[ ! -e "$app_dir" && -d "$previous_app" ]]; then
        mv -- "$previous_app" "$app_dir" || recovery_failed=1
      else
        recovery_failed=1
      fi
    fi
    if [[ "$had_old_commit" == "1" ]]; then
      if cp -p -- "$previous_commit" "$restore_commit" && mv -f -- "$restore_commit" "$old_commit_file"; then
        :
      else
        recovery_failed=1
      fi
    else
      rm -f -- "$old_commit_file" || recovery_failed=1
    fi
    if [[ "$recovery_failed" != "0" ]]; then
      printf 'CRITICAL: post-activation verification failed and automatic restoration was incomplete. Transaction: %s; backup: %s\n' "$transaction_dir" "$backup_app" >&2
      return 1
    fi
    rm -rf -- "$transaction_dir"
    printf 'Post-activation verification failed; prior application and marker restored.\n' >&2
    return 1
  fi

  if [[ -n "$transaction_dir" ]] && ! rm -rf -- "$transaction_dir"; then
    printf 'Warning: deployment succeeded but transaction cleanup failed: %s\n' "$transaction_dir" >&2
  fi
  printf 'Application deployed and compiled successfully.\n'
  printf 'Installed commit: %s\n' "$commit"
  if [[ "$had_old_app" == "1" ]]; then
    printf 'Recovery backup retained at: %s\n' "$backup_app"
  fi
)
