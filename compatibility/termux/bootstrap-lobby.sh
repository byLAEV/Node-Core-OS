#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

REPOSITORY_OWNER="byLAEV"
REPOSITORY_NAME="Node-Core-OS"
DEFAULT_REF="feature/lobby-2.0-clean-main"
SOURCE_REF="${NODE_CORE_LOBBY_REF:-$DEFAULT_REF}"

usage() {
  cat <<'EOF'
NODE CORE OS Lobby — remote Linux terminal bootstrap

Usage:
  bash bootstrap-lobby.sh [--yes]

Options:
  --yes   Approve installation of openssl-tool if the Lobby installer needs it.

Source selection:
  NODE_CORE_LOBBY_REF=main bash bootstrap-lobby.sh

The bootstrap downloads a commit-pinned source snapshot from the official
GitHub repository, then runs compatibility/termux/install-lobby.sh.
It installs the Lobby only. It does not install or update Node Core OS.
EOF
}

INSTALLER_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --yes) INSTALLER_ARGS+=(--yes) ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$arg" >&2; usage >&2; exit 2 ;;
  esac
done

fail() { printf 'NODE CORE OS Lobby bootstrap ERROR: %s\n' "$*" >&2; exit 1; }
info() { printf '[NODE CORE OS Lobby] %s\n' "$*"; }

[[ -n "${HOME:-}" && -d "$HOME" ]] || fail "HOME is missing or unavailable."
[[ "$(uname -s)" == "Linux" ]] || fail "Run this bootstrap inside a Linux terminal environment."
[[ "$(id -u)" != "0" ]] || fail "Do not run the Lobby installer as root."

ARCH="$(uname -m)"
case "$ARCH" in
  aarch64|arm64|x86_64|amd64) ;;
  *) fail "Unsupported Linux architecture for the Lobby: $ARCH" ;;
esac

for command_name in curl tar bash; do
  command -v "$command_name" >/dev/null 2>&1 || \
    fail "Missing command '$command_name'. Install it using your Linux distribution policy before retrying."
done
PYTHON="$(command -v python3 || command -v python || true)"
[[ -n "$PYTHON" ]] || fail "Python 3 is required."

[[ "$SOURCE_REF" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]] || fail "Invalid source ref."
[[ "$SOURCE_REF" != *".."* && "$SOURCE_REF" != *"//"* && "$SOURCE_REF" != */ ]] || \
  fail "Unsafe source ref."

WORK_DIR="$(mktemp -d "$HOME/.node-core-lobby-bootstrap.XXXXXX")" || fail "Could not create a temporary directory."
cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

BRANCH_JSON="$WORK_DIR/branch.json"
ARCHIVE="$WORK_DIR/source.tar.gz"
EXTRACT_DIR="$WORK_DIR/source"
mkdir -m 700 "$EXTRACT_DIR"

ENCODED_REF="$("$PYTHON" -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$SOURCE_REF")"
BRANCH_URL="https://api.github.com/repos/$REPOSITORY_OWNER/$REPOSITORY_NAME/branches/$ENCODED_REF"

info "Resolving the official source ref: $SOURCE_REF"
curl --http1.1 --fail --location --silent --show-error \
  --connect-timeout 15 --max-time 90 --retry 5 --retry-all-errors --retry-delay 2 \
  --header "Accept: application/vnd.github+json" \
  --header "User-Agent: Node-Core-OS-Lobby-Installer" \
  --output "$BRANCH_JSON" "$BRANCH_URL" || fail "Could not resolve the source ref from GitHub after 5 retries. Check GitHub/network connectivity and retry."

COMMIT="$("$PYTHON" - "$BRANCH_JSON" <<'PY'
import json
import re
import sys
from pathlib import Path

try:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    commit = payload["commit"]["sha"]
except (OSError, ValueError, KeyError, TypeError) as exc:
    raise SystemExit(f"Invalid GitHub branch response: {exc}")
if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
    raise SystemExit("GitHub returned an invalid commit SHA.")
print(commit)
PY
)" || fail "Could not validate the official source commit."

ARCHIVE_URL="https://codeload.github.com/$REPOSITORY_OWNER/$REPOSITORY_NAME/tar.gz/$COMMIT"
info "Downloading verified-ref snapshot at commit $COMMIT"
curl --http1.1 --fail --location --silent --show-error \
  --connect-timeout 15 --max-time 240 --retry 5 --retry-all-errors --retry-delay 2 \
  --output "$ARCHIVE" "$ARCHIVE_URL" || fail "Could not download the official source snapshot after 5 retries."

info "Extracting the source snapshot into a private temporary directory."
"$PYTHON" - "$ARCHIVE" "$EXTRACT_DIR" <<'PY'
import os
import shutil
import sys
import tarfile
from pathlib import Path, PurePosixPath

archive_path = Path(sys.argv[1])
destination = Path(sys.argv[2]).resolve()

with tarfile.open(archive_path, "r:gz") as archive:
    members = archive.getmembers()
    if not members:
        raise SystemExit("The official source archive is empty.")

    for member in members:
        name = PurePosixPath(member.name)
        if name.is_absolute() or not name.parts or ".." in name.parts:
            raise SystemExit(f"Unsafe path in source archive: {member.name!r}")
        if not (member.isdir() or member.isfile()):
            # Git archive symlinks and special files are not needed by the Lobby
            # installer; do not materialize them in the temporary directory.
            continue

        target = destination.joinpath(*name.parts)
        if os.path.commonpath((str(destination), str(target.resolve()))) != str(destination):
            raise SystemExit(f"Archive path escapes extraction directory: {member.name!r}")

        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        source = archive.extractfile(member)
        if source is None:
            raise SystemExit(f"Could not read archive member: {member.name!r}")
        with source, target.open("xb") as output:
            shutil.copyfileobj(source, output)
        os.chmod(target, member.mode & 0o777 & ~0o6000)
PY

SOURCE_ROOT=""
for candidate in "$EXTRACT_DIR"/Node-Core-OS-*; do
  if [[ -d "$candidate" && -f "$candidate/compatibility/termux/install-lobby.sh" ]]; then
    SOURCE_ROOT="$candidate"
    break
  fi
done
[[ -n "$SOURCE_ROOT" ]] || fail "The downloaded source does not contain the official Termux Lobby installer."

info "Source commit: $COMMIT"
info "Installing the Lobby application and Termux:Widget shortcut."
bash "$SOURCE_ROOT/compatibility/termux/install-lobby.sh" "${INSTALLER_ARGS[@]}"

info "Lobby bootstrap completed. Node Core OS itself was not installed or updated."
