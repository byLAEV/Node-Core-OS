#!/usr/bin/env bash
set -euo pipefail

# Optional live test. This contacts public OpenTimestamps calendars and may
# leave a synthetic timestamp request in their queues.
if [[ "$(id -u)" == "0" ]]; then
  printf 'Refusing live OpenTimestamps integration test as root. Run as a normal user.\n' >&2
  exit 1
fi

for command in python3 timeout; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'Required command not found: %s\n' "$command" >&2
    exit 1
  }
done

tmp_root="$(mktemp -d)"
trap 'rm -rf "$tmp_root"' EXIT
venv="$tmp_root/venv"
document="$tmp_root/node-core-opentimestamps-smoke.md"
proof="$document.ots"

python3 -m venv "$venv"
"$venv/bin/python" -m pip install --disable-pip-version-check --upgrade pip
"$venv/bin/python" -m pip install --disable-pip-version-check opentimestamps-client

"$venv/bin/ots" --help >/dev/null
"$venv/bin/python" -c 'import opentimestamps'
printf '# Node Core OS OpenTimestamps integration smoke test\nSynthetic test data only.\n' > "$document"
before="$(sha256sum "$document" | awk '{print $1}')"

printf 'Submitting a synthetic document to the official OpenTimestamps client...\n'
timeout 180 "$venv/bin/ots" stamp "$document"

[[ -s "$proof" ]] || {
  printf 'OpenTimestamps did not create a non-empty proof file.\n' >&2
  exit 1
}
after="$(sha256sum "$document" | awk '{print $1}')"
[[ "$before" == "$after" ]] || {
  printf 'Original document changed during timestamp submission.\n' >&2
  exit 1
}

printf 'Checking the newly created proof...\n'
set +e
verify_output="$(timeout 180 "$venv/bin/ots" verify "$document" 2>&1)"
verify_status=$?
set -e
printf '%s\n' "$verify_output"

# The initial proof may be pending while Bitcoin confirmation is unavailable.
# The CLI must nevertheless execute successfully or clearly report a pending
# calendar state. Any unrelated CLI/runtime error fails this test.
if [[ "$verify_status" -ne 0 ]]; then
  if ! grep -Eiq 'pending|not yet|calendar|bitcoin blockchain|upgrade' <<< "$verify_output"; then
    printf 'Proof verification command failed for an unexpected reason (exit %s).\n' "$verify_status" >&2
    exit "$verify_status"
  fi
fi

printf 'OpenTimestamps live integration smoke test completed.\n'
printf 'Proof state must be interpreted from the CLI output; a pending proof is not Bitcoin-confirmed.\n'
