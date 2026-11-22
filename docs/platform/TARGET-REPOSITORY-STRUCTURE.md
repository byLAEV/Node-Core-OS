# Target Repository Structure — Node Core OS Linux-only

**Repository:** `byLAEV/Node-Core-OS`  
**Target branch for this architecture:** `strategy/linux-only-lindesk-android-access`  
**Status:** proposed target layout; not yet migrated into `main`.

## 1. Platform rule

- Node Core OS runtime, services, storage, identity, Kubo and applications execute on GNU/Linux only.
- Lindesk is an independently built Android client for authenticated access to, administration of, and user-approved installation of Node Core OS on a Linux host.
- Android/Termux is not a Node Core OS runtime or installation target.
- The Android client must use a versioned Node Core API. It must not import Python internals, read Linux filesystem paths directly, run Kubo itself, or receive Linux node private keys by default.
- The Linux host owns local storage, node identity, Kubo/IPFS, protocols and application execution.

## 2. Target root tree

The tree below describes the intended organization. Some leaves are existing code; others are new organizational destinations to be created only as part of tested migrations. It is not a claim that all listed modules already exist.

```text
Node-Core-OS/
├── .github/
│   ├── workflows/                         # all workflow YAML files remain directly here
│   │   ├── linux-core-ci.yml
│   │   ├── linux-installer-e2e.yml
│   │   ├── linux-distribution-matrix.yml
│   │   ├── linux-network-p2p-e2e.yml
│   │   ├── security-certificate-tests.yml
│   │   ├── security-catalog-integrity.yml
│   │   ├── applications-<name>.yml
│   │   ├── lindesk-android-ci.yml
│   │   ├── docs-pages.yml
│   │   └── release-verified.yml
│   └── ...
│
├── README.md
├── VERSION
├── CHANGELOG.md
├── LICENSE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md                            # add security reporting policy
├── main.py                                # stable Python entry point
├── requirements.txt                       # current runtime requirements; refine later
│
├── node_core/                             # ONLY Node Core OS runtime package
│   ├── __init__.py
│   ├── runtime.py
│   ├── bios.py
│   ├── config.py
│   ├── compatibility/
│   │   ├── __init__.py
│   │   ├── detection.py
│   │   └── policy.py                     # Linux policy only
│   ├── platform/
│   │   └── linux/
│   │       ├── distribution.py
│   │       ├── filesystem.py
│   │       ├── service_manager.py
│   │       ├── process.py
│   │       └── kubo_runtime.py
│   ├── storage/
│   │   ├── local_storage.py
│   │   ├── registry.py
│   │   └── lifecycle.py
│   ├── content/
│   │   ├── manager.py
│   │   ├── ipfs.py
│   │   └── external_cids.py
│   ├── identity/
│   │   ├── node_identity.py
│   │   ├── profile.py
│   │   ├── associations.py
│   │   ├── entity_registry.py
│   │   ├── function_proof.py
│   │   └── presence.py
│   ├── security/
│   │   ├── crypto_health.py
│   │   ├── certificates/
│   │   ├── pki_guard/
│   │   ├── utxo/
│   │   ├── shield/
│   │   └── cdd/
│   ├── networking/
│   │   ├── diagnostics.py
│   │   ├── p2p/
│   │   ├── relay/
│   │   ├── replication/
│   │   └── reputation/
│   ├── protocols/
│   ├── services/
│   ├── api/
│   │   ├── v1/
│   │   ├── authentication/
│   │   └── authorization/
│   ├── interfaces/
│   │   ├── terminal/
│   │   └── web/
│   └── lifecycle/
│       └── updates.py
│
├── platform/                              # host integrations; never Android runtime
│   └── linux/
│       ├── README.md
│       ├── systemd-user/
│       ├── distro/
│       ├── packages/
│       └── kubo/
│
├── compatibility/
│   └── linux/
│       └── manifest.json                  # only GNU/Linux profiles and tested architectures
│
├── installer/
│   ├── linux/
│   │   ├── install.sh
│   │   ├── update.sh
│   │   ├── uninstall.sh
│   │   └── lib/
│   │       ├── detect.sh
│   │       ├── dependencies.sh
│   │       ├── filesystem.sh
│   │       ├── kubo.sh
│   │       ├── service.sh
│   │       └── verify.sh
│   ├── manifests/
│   └── tests/
│       ├── preflight/
│       ├── install/
│       ├── update/
│       ├── uninstall/
│       └── data-preservation/
│
├── clients/
│   └── lindesk-android/                   # independent Android app/client
│       ├── README.md
│       ├── docs/
│       │   ├── ARCHITECTURE.md
│       │   ├── ENROLLMENT.md
│       │   ├── SECURITY.md
│       │   └── LINUX-INSTALL-FLOW.md
│       ├── app/
│       │   └── src/
│       │       ├── main/
│       │       └── test/
│       ├── api-contract/
│       ├── tests/
│       └── build files                    # selected Android framework's build files
│
├── applications/
│   ├── my-life/                           # personal blog; core storage via API
│   ├── about-us/                          # only when its implementation is approved
│   ├── hashpaper/
│   ├── node-core-music/
│   ├── openpgp/
│   ├── p2p-contracts/
│   └── eulora2-transponder/
│
├── tools/
│   ├── README.md
│   ├── catalog/
│   ├── attestations/
│   ├── cmi-scc/
│   ├── credential-verification/
│   ├── node-security/
│   ├── operator-services/
│   └── node-pki-guard-cli/
│
├── catalogs/
│   └── node-network-certificates/
│       ├── README.md
│       ├── certificates/
│       ├── evidence/
│       └── audit/
│
├── schemas/
│   ├── compatibility/
│   ├── identity/
│   ├── certificates/
│   ├── content/
│   ├── networking/
│   ├── api/
│   └── applications/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   ├── identity/
│   ├── storage/
│   ├── content-ipfs/
│   ├── networking-p2p/
│   ├── api/
│   ├── applications/
│   └── regression/
│
├── ci/
│   └── linux/
│       ├── Dockerfile
│       ├── run-user-e2e.sh
│       ├── run-manual-mesh.sh
│       ├── three-node-native-p2p.py
│       └── real_multi_node_mesh.py
│
├── scripts/
│   ├── audit/
│   ├── validation/
│   ├── release/
│   └── operations/
│
├── docs/
│   ├── README.md
│   ├── architecture/
│   ├── platform/
│   │   ├── linux/
│   │   └── lindesk-android/
│   ├── installation/
│   ├── storage-ipfs/
│   ├── identity/
│   ├── security-certificates/
│   ├── networking-p2p/
│   ├── protocols/
│   ├── applications/
│   ├── api/
│   ├── operations/
│   ├── testing-evidence/
│   ├── release/
│   ├── migration/
│   └── adr/
│
├── research/
│   ├── roadmap/
│   ├── institutional-identity/
│   ├── global-mapping/
│   ├── business-models/
│   └── design-methodology/
│
├── prototypes/
│   └── web-test-bench/
│
├── templates/
│   └── client/
│
├── examples/
├── release/
└── archive/
    └── termux-reference/                  # historical-only; never part of active CI/release
```

## 3. Mapping from current main to target

| Current path in main | Target path / action |
|---|---|
| `main.py` | Keep at repository root as the stable entry point. |
| `node_core/` | Keep as the only runtime package; reorganize its modules into clear subpackages gradually. Do not create a parallel `core/`. |
| `node_core/storage.py`, `content.py`, `ipfs.py`, `external_cids.py` | Move responsibilities into `node_core/storage/` and `node_core/content/` after import and installer tests exist. |
| `node_core/network.py`, `network_diagnostics.py`, `p2p/`, `record_replication.py`, `relay_delivery.py`, `reputation/` | Consolidate under `node_core/networking/`. |
| `node_core/security/*` | Keep the security domain together; group PKI Guard, certificates, UTXO, Shield and CDD by responsibility without changing cryptographic formats. |
| `node_core/web*`, `node_core/ui.py` | Move to `node_core/interfaces/` only after entry-point and route tests are updated. |
| `compatibility/manifest.json` | Move to `compatibility/linux/manifest.json`; only GNU/Linux runtime profiles remain active. |
| `installer/*` | Move active scripts to `installer/linux/`; preserve a temporary root wrapper if required for backward compatibility. |
| `installer/termux-install.sh`, Termux installer tests | Move to `archive/termux-reference/` after active references are removed and historical purpose is documented. |
| `.github/workflows/*termux*` | Disable and archive or replace with Linux-negative tests proving Android/Termux rejection. Do not execute as active Node Core CI. |
| `tools/termux_remote_kubo_read.py`, `docs/TERMUX*.md`, `tests/test_termux*` | Archive as historical research or replace with Lindesk API/client tests where relevant. |
| `applications/*` | Keep each application isolated; each gets its own manifest, README, dependencies and tests. No app may bypass core authorization/storage APIs. |
| `client-template/` | Move to `templates/client/`. |
| `web-test-bench/` | Move to `prototypes/web-test-bench/`; do not treat prototypes as production interfaces. |
| `ci/linux/` | Keep under `ci/linux/`; it becomes the canonical runtime E2E harness. |
| `docs/*.md` | Sort by domain under the new `docs/` subdirectories; update all relative links. |
| `RoadMap Index/` | Move to `research/roadmap/` and keep current roadmap entry points linked from docs. |
| Long root certificate catalog directory | Move to `catalogs/node-network-certificates/`; preserve certificate IDs, evidence, schemas and package checksums. |
| Root research CSVs and research notes | Move to `research/institutional-identity/` or `research/global-mapping/`; preserve source data and provenance. |
| `tests/test_*.py` | Group by unit/integration/security/domain only after pytest/unittest discovery and CI paths are updated. |
| `schemas/`, `scripts/`, `release/`, `examples/`, `tools/` | Keep their roles, then organize by domain where beneficial. |

## 4. Lindesk boundary and security contract

Lindesk is a client, not a Linux node and not an Android port of the runtime.

Lindesk may:
- Pair with a Linux node using explicit user authorization.
- Read status and health exposed by the authenticated Node Core API.
- Create or revoke client sessions and scoped permissions.
- Guide a user through a Linux installation, or start a clearly disclosed and confirmed deployment process.
- Display installation progress, node identity, Kubo status and application status returned by the API.

Lindesk must not:
- Run the Node Core OS Python runtime or Kubo as its local backend.
- Use Android Termux as an alternative Node Core host.
- Directly access the Linux node's filesystem or private keys.
- Expose Kubo's administrative RPC to the public network.
- silently run root commands, install software, publish IPFS content, or delete user data.
- turn a phone pairing into unrestricted administrator authority.

## 5. Rules for restructuring

1. First create a complete path inventory and record the current `main` commit and test baseline.
2. Migrate one domain at a time, preserving Git history where possible.
3. Update imports, packaging manifests, installer file lists, workflows, docs links and tests together.
4. Keep data under `~/.node-core/` outside the replaceable source-code tree.
5. Never delete identity keys, user storage, certificate evidence or application data during source migration.
6. Keep Termux references in a historical archive only when they are valuable for traceability; do not ship or execute them.
7. Do not create placeholder code and describe it as implemented.
8. Every target distribution and architecture requires its own successful Linux installation evidence.
9. Lindesk needs independent Android build, API compatibility and authentication tests.
10. Keep the migration in a branch and merge only after the full required checks pass.

## 6. Migration order

1. Root inventory, dependency graph and passing baseline.
2. Publish the Linux-only platform contract and target structure.
3. Migrate compatibility manifest and reject Android/Termux before installer mutation.
4. Reorganize Linux installer and preserve update/uninstall data-safety guarantees.
5. Consolidate `node_core/` packages without changing public contracts.
6. Introduce and test the authenticated Node Core API used by Lindesk.
7. Create the independent Lindesk Android client.
8. Reorganize applications, schemas, tests, tools, catalogs, research and docs.
9. Replace or archive Termux CI and historical runtime code.
10. Run Linux distribution, storage, IPFS, identity, certificate, network and release regression tests.

**No mass deletion or directory-wide move is authorized by this tree.** The migration must be incremental and each step independently reviewable.
