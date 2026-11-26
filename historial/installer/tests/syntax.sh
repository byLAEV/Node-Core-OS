#!/usr/bin/env bash
set -euo pipefail

for file in installer/*.sh installer/lib/*.sh installer/tests/*.sh; do
  bash -n "$file"
done

printf 'Installer shell syntax: OK\n'
