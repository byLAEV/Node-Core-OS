#!/usr/bin/env bash
set -euo pipefail

# Read-only planner. It reports proposed actions but never applies them.
# Actual files are authoritative; the manifest is metadata and cannot override
# missing or incomplete files discovered by the detector.

NODE_CORE_PLAN_ACTIONS=()
NODE_CORE_PLAN_MODE="install"
NODE_CORE_PLAN_MANIFEST_STATUS="missing"

node_core_plan_installation() {
  local report app launcher update_launcher kubo ipfs_repo storage config manifest
  local manifest_path="${NODE_CORE_DATA_DIR:-$HOME/.node-core}/installation-manifest.json"

  # shellcheck source=detect.sh
  source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/detect.sh"
  # shellcheck source=manifest.sh
  source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/manifest.sh"

  NODE_CORE_PLAN_ACTIONS=()
  report="$(node_core_detect_installation)"

  app="$(awk -F= '$1=="application"{print $2}' <<<"$report")"
  launcher="$(awk -F= '$1=="launcher"{print $2}' <<<"$report")"
  update_launcher="$(awk -F= '$1=="update_launcher"{print $2}' <<<"$report")"
  kubo="$(awk -F= '$1=="kubo"{print $2}' <<<"$report")"
  ipfs_repo="$(awk -F= '$1=="ipfs_repository"{print $2}' <<<"$report")"
  storage="$(awk -F= '$1=="local_storage"{print $2}' <<<"$report")"
  config="$(awk -F= '$1=="configuration"{print $2}' <<<"$report")"
  manifest="$(awk -F= '$1=="manifest"{print $2}' <<<"$report")"

  if [[ "$manifest" == "present" ]]; then
    if node_core_manifest_validate "$manifest_path" >/dev/null 2>&1; then
      NODE_CORE_PLAN_MANIFEST_STATUS="valid"
    else
      NODE_CORE_PLAN_MANIFEST_STATUS="invalid"
    fi
  fi

  if [[ "$app" == "missing" ]]; then
    NODE_CORE_PLAN_MODE="install"
    NODE_CORE_PLAN_ACTIONS+=("install_application")
  elif [[ "$app" == "incomplete" ]]; then
    NODE_CORE_PLAN_MODE="repair"
    NODE_CORE_PLAN_ACTIONS+=("repair_application")
  else
    NODE_CORE_PLAN_MODE="update_or_verify"
    NODE_CORE_PLAN_ACTIONS+=("check_application_version")
  fi

  [[ "$launcher" == "present" ]] || NODE_CORE_PLAN_ACTIONS+=("create_application_launcher")
  [[ "$update_launcher" == "present" ]] || NODE_CORE_PLAN_ACTIONS+=("create_update_launcher")

  # Never install/replace Kubo automatically in the planner. Missing Kubo is a
  # reported prerequisite requiring an explicit, separately verified action.
  [[ "$kubo" == "present" ]] || NODE_CORE_PLAN_ACTIONS+=("review_missing_kubo")
  [[ "$ipfs_repo" == "present" ]] || NODE_CORE_PLAN_ACTIONS+=("review_missing_ipfs_repository")
  [[ "$storage" == "present" ]] || NODE_CORE_PLAN_ACTIONS+=("create_local_storage_directory")
  [[ "$config" == "valid" ]] || NODE_CORE_PLAN_ACTIONS+=("review_configuration")

  if [[ "$NODE_CORE_PLAN_MANIFEST_STATUS" != "valid" ]]; then
    NODE_CORE_PLAN_ACTIONS+=("write_verified_manifest_after_apply")
  fi

  printf 'mode=%s\n' "$NODE_CORE_PLAN_MODE"
  printf 'manifest_status=%s\n' "$NODE_CORE_PLAN_MANIFEST_STATUS"
  printf 'actions_count=%s\n' "${#NODE_CORE_PLAN_ACTIONS[@]}"
  local action
  for action in "${NODE_CORE_PLAN_ACTIONS[@]}"; do
    printf 'action=%s\n' "$action"
  done
}
