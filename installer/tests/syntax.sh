#!/usr/bin/env bash
set -euo pipefail

for file in installer/install.sh installer/uninstall.sh installer/lib/*.sh; do
  bash -n "$file"
done

printf 'Installer shell syntax: OK\n'
