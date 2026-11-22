# Linux-Only Platform Strategy and Repository Restructuring

**Status:** Approved architectural direction; migration plan.
**Decision:** Node Core OS runtime and supported installation targets are GNU/Linux only. Android is not a runtime target for Node Core OS.

## 1. Platform boundary

- **Node Core OS:** executes on supported GNU/Linux distributions and architectures declared by a tested compatibility manifest.
- **Lindesk for Android:** a separate client/access and installation interface. It may guide installation, connect to an authorized Linux node, display status, and initiate explicitly approved operations through a documented API.
- **Android / Termux:** not a Node Core OS runtime, host installation profile, or supported substitute for GNU/Linux. Android compatibility code must not silently remain in the core installer.
- **Kubo/IPFS:** runs as a Linux-side service managed by Node Core OS. Lindesk must access it only through Node Core OS's authorized interface, never through an exposed administrative RPC.

## 2. Restructuring principles

1. Audit before moving, deleting, renaming, or rewriting files.
2. Preserve Git history and persistent user data; do not perform destructive bulk moves.
3. Keep runtime, installer, platform adapters, applications, interfaces, documentation, and tests separated.
4. Treat each migration as a small, reviewable change with a clear acceptance test.
5. Do not claim a capability is functional until implementation and tests demonstrate it.
6. Keep public/private/IPFS/temporary storage boundaries explicit.
7. Secrets, private keys, credentials, and personal data must never be copied into Lindesk logs, packages, or public content by default.

## 3. Target repository organization

This is a target logical organization, not an instruction to create empty folders or move all existing files immediately. Map each existing path before migration.

```text
Node-Core-OS/
├── core/                 # runtime, boot, lifecycle, core contracts
├── services/              # storage, Kubo adapter, identity, APIs
├── applications/          # first-party applications using core contracts
├── platform/
│   └── linux/             # Linux detection, service and package adapters
├── installer/
│   ├── linux/             # Linux install/update/uninstall entry points
│   └── tests/
├── lindesk/               # Android client and Linux-node access/install UX
├── docs/
│   ├── architecture/
│   ├── platform/
│   ├── migration/
│   └── applications/
├── schemas/               # versioned manifests and API/data contracts
├── tests/                 # unit, integration, installer and Linux E2E
├── scripts/               # reproducible developer and maintenance scripts
└── .github/workflows/      # Linux-only CI and release validation
```

The current repository already has established directories such as `node_core/`, `applications/`, `installer/`, `compatibility/`, `docs/`, `schemas/`, and `tests/`. Prefer improving and documenting these in place first; do not duplicate the runtime into a new `core/` directory unless a tested migration justifies it.

## 4. Workstreams

### A. Repository inventory and baseline
- Record current branch, commit, tracked paths, entry points, package dependencies, workflows, installer scripts, and tests.
- Identify Android/Termux-specific assumptions by searching for platform markers, package managers, paths, and workflow names.
- Categorize every finding as: Linux core, Android Lindesk client, cross-platform protocol/schema, historical research, or unresolved.
- Capture the baseline test results before changing behavior.

### B. Runtime and compatibility
- Make the compatibility manifest define GNU/Linux as the only supported runtime family.
- Keep architecture support limited to architectures with actual CI and installer evidence.
- Remove Termux as a Node Core installation/runtime profile only after references, tests, and documentation are migrated.
- Retain generic POSIX terminal capability detection; terminal emulator brands are not operating-system targets.
- Do not require systemd; keep it an optional Linux service adapter where already supported.

### C. Installer and lifecycle
- Canonical install, update, verification, and uninstall paths target GNU/Linux.
- Installer must reject Android/Termux before dependency installation or filesystem mutation.
- No root execution; preserve existing user-level installation and data-safety protections.
- Ensure update and uninstall preserve or explicitly confirm handling of persistent data.
- Do not delete application code as a workaround for platform migration; use explicit packaging manifests and exclusion rules.

### D. Lindesk Android client
- Define Lindesk as a separate client project/module with its own build, release, and test lifecycle.
- Provide a secure enrollment flow and authenticated Linux-node connection.
- Use a versioned, documented Node Core API; do not couple the Android client to internal Python modules or filesystem paths.
- Provide installation guidance or an authorized deployment mechanism for Linux. Any remote install must show the target, actions, privileges, and user confirmation.
- Android stores only client configuration and required session material, protected by platform security. Node private keys and identity authority remain on the Linux node unless a separately reviewed protocol explicitly permits delegation.

### E. Storage, IPFS, identity and applications
- Linux owns local storage, node identity, Kubo process and persistent application data.
- Preserve distinct local, public, IPFS-CID, private, and temporary/forgetting lifecycle semantics where implemented.
- Applications use documented core interfaces and must not assume Android execution.
- Separate platform-specific UI/client code from shared protocol schemas and documentation.

### F. CI, tests and release
- CI runs supported Linux unit, integration, installer, update-safety, and Kubo contract tests.
- Add a negative test proving Android/Termux is rejected before installer mutation.
- Lindesk has independent Android build and client/API compatibility tests.
- Release artifacts clearly distinguish Linux Node Core packages from Lindesk Android client packages.
- Release evidence must identify commit, supported distro/architecture, commands, results, and known limitations.

## 5. Migration sequence

1. **Freeze scope and inventory:** no mass moves; establish baseline.
2. **Publish this platform contract:** document Linux-only runtime and Lindesk boundary.
3. **Correct compatibility contract and tests:** Linux profiles only; Android rejected.
4. **Clean installer and CI:** remove Android runtime paths, preserve tested Linux behavior.
5. **Separate Lindesk client/API:** establish independent module and interface.
6. **Map and migrate applications:** classify each application and fix platform assumptions individually.
7. **Consolidate documentation and release manifests:** remove contradictions, retain historical records with labels.
8. **Run full regression and release audit:** no migration considered complete without evidence.

## 6. Acceptance criteria

- README and canonical architecture consistently say GNU/Linux-only runtime.
- Compatibility manifest, installer, and CI agree on supported Linux targets.
- Android/Termux installer attempts fail safely before mutation.
- Lindesk is described and packaged as an Android access/install client, not as Node Core OS runtime.
- No duplicate core runtime or unverified bulk relocation is introduced.
- Existing verified Linux functionality and persistent data are preserved.
- Each migrated feature has traceable tests and a documented status.

## 7. Explicitly not authorized by this plan

This document does not authorize deleting repository history, removing existing applications or certificates, changing cryptographic formats, exposing Kubo RPC, installing software remotely without consent, or claiming Linux distribution support without tests. Such changes require their own scoped implementation and review.
