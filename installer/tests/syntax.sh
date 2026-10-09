#!/usr/bin/env bash
set -euo pipefail

for file in installer/install.sh installer/update.sh installer/uninstall.sh installer/lib/*.sh installer/tests/*.sh; do
  bash -n "$file"
done

printf 'Installer shell syntax: OK\n'
