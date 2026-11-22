# Repository migration map

**Status:** staged physical directory scaffolding; source-to-destination moves are not yet complete.

| Current source area | Target area | Migration policy |
|---|---|---|
| `node_core/` | `node_core/` (canonical runtime) | Keep established package; reorganize modules internally only with import and tests updated. |
| `compatibility/` | `platform/linux/` plus shared contracts | Move Linux detection/adapters after dependency and test audit; schemas remain shared. |
| `installer/` | `installer/linux/` | Existing top-level installer remains canonical until parity and regression tests pass. |
| Android client code (inventory required) | `clients/lindesk-android/` | Separate Android build/API client; no runtime imports. |
| `applications/` | `applications/` | Keep app boundaries; each app documents core API dependencies and storage scope. |
| Existing identity/certificate tools and catalogs | `catalogs/node-network-certificates/` and existing `tools/` | Inventory first; distinguish public catalog data from sensitive local evidence. |
| `docs/*.md` | `docs/architecture/`, `docs/platform/`, `docs/migration/` | Move in batches; update all Markdown links and CI references. |
| `schemas/` | `schemas/` | Keep stable, versioned contracts; do not bury schemas inside platform modules. |
| `tests/` and installer tests | `tests/`, `installer/tests/`, Lindesk tests | Keep tests adjacent only where project conventions support it; maintain test discovery. |
| Termux-specific history | `archive/termux-reference/` | Archive docs only after ensuring no active execution path depends on them. |

## Required completion gate

A row is complete only when: source and destination are recorded; references/imports/workflows are updated; no duplicate active implementation remains; tests run on declared Linux targets; unsupported Android/Termux installation fails before mutation; documentation accurately distinguishes implemented and planned behavior.
