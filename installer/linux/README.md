# GNU/Linux installer module

The canonical installer currently remains at `installer/install.sh` with shared safety helpers under `installer/lib/`. This directory is the target for Linux-specific install, update and uninstall entry points.

Migration must preserve current install/update protections, data retention guarantees, non-root policy and reject unsupported platforms before mutation. The canonical entry point will not be changed until parity tests pass.
