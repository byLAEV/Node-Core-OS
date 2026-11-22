#!/usr/bin/env bash
set -euo pipefail

# Retained temporarily so existing command references fail safely and clearly.
# Android/Termux is not a Node Core OS runtime or installation target.
printf '%s\n' 'Node Core OS is supported on GNU/Linux only.' >&2
printf '%s\n' 'Android users should use Lindesk to access or install a Node Core OS Linux node.' >&2
printf '%s\n' 'This legacy Termux installer does not install, update, or modify Node Core OS.' >&2
exit 1
