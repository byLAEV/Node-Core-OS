# PR #192 — CI failure analysis and corrective changes

Date: 2026-10-31  
Repository: byLAEV/Node-Core-OS  
Branch: feat/github-pages-node-binding

## Source run and tested revision

The failures below were observed in GitHub Actions for merge commit
`d36c21046b69de74f0dab824e825bcf0da929e53`, containing PR head
`51924263fb1b198e13dc234687e858d03ac40f22`.

## Findings

### 1. Three-distribution native P2P ring

Workflow run: https://github.com/byLAEV/Node-Core-OS/actions/runs/41191237295

The three containers built successfully, the application installed as UID 1001
on Ubuntu 24.04, Debian 13 and Fedora 44, unique node identities were prepared,
and all three authenticated listeners started.

Record delivery failed on the duplicate-delivery operation. The first send used
the Docker network alias `node-b`; the second send used the short label `b`.
The latter was not a resolvable network hostname and produced
`socket.gaierror: [Errno -3] Temporary failure in name resolution`.

Correction:
- Both deliveries now use the same Docker network alias, `node-<label>`.
- The receiver persistence and Kubo cross-distro steps remain downstream gates
  and must pass in a new run before this test is considered complete.

### 2. HTTPS test certificate compatibility

Workflow run: https://github.com/byLAEV/Node-Core-OS/actions/runs/41191237298

The valid-chain TLS test failed on the system OpenSSL policy because the
synthetic CA/leaf chain omitted Subject Key Identifier and Authority Key
Identifier extensions.

Correction:
- Synthetic CA certificates now include Subject Key Identifier.
- Synthetic leaf certificates now include Authority Key Identifier derived
  from the issuer public key.
- The actual TLS handshake and hostname validation remain enabled; verification
  was not disabled or weakened.

### 3. Web2 stress evidence paths on read-only source mounts

Workflow runs:
- https://github.com/byLAEV/Node-Core-OS/actions/runs/41191237295
- https://github.com/byLAEV/Node-Core-OS/actions/runs/41191237298

The distro E2E mounts the repository at `/workspace:ro`. Two stress tests
attempted to create evidence under relative `artifacts/`, causing
`OSError: [Errno 30] Read-only file system`. This was an evidence-output
location defect, not an observed failed security assertion.

Correction:
- Both stress tests write to `NODE_CORE_TEST_ARTIFACTS_DIR`, defaulting to a
  temporary writable directory.
- The distro E2E workflow explicitly sets this variable to
  `/tmp/node-core-test-artifacts`.

## Corrective commits

- `6d515e2e29d1a76065cba280c76a8c8e47070a53` — use the resolvable network alias for duplicate P2P delivery.
- `b932a35c6aef80fc01e199d12f84999df684d338` — add standard X.509 key identifier extensions to test certificates.
- `370721f00319810dda896efa5a0d0ebf42d2e5a9` — write heavy stress evidence to a writable artifact directory.
- `1480d36020d023cd4045aadce5e9d110829712f3` — write persistent stress evidence to a writable artifact directory.
- `1532d3178e6504acf8e93ad4213900427aae73ca` — configure the writable evidence directory in distro E2E.

## Verification status

A new workflow batch was queued for revision
`1532d3178e6504acf8e93ad4213900427aae73ca`. Queued is not passed.
The native three-distribution P2P test and complete distro lifecycle must finish
successfully before PR #192 can be considered validated.

All product execution remains as an ordinary user; privileged operations are
limited to preparing the isolated CI container images.


## 4. BIOS menu navigation and non-root distro lifecycle

Workflow run: https://github.com/byLAEV/Node-Core-OS/actions/runs/41196769035

The BIOS menu smoke test completed on Ubuntu 24.04, Debian 13 and Fedora 44.
The new test `test_bios_back_returns_to_os_menu_and_os_zero_exits` passed in
all three installed application suites. This confirms the menu hierarchy:
submenu `0` returns to BIOS, BIOS `0` returns to Node Core OS, and the
Node Core OS main-menu `0` exits the application.

The full installed test suite completed with 408 tests and `OK` on Debian 13
and Ubuntu 24.04. Fedora's installed suite also reported `OK`; the captured
log includes expected BrokenPipeError diagnostics from HTTP tests that close
client sockets early, while those tests themselves passed.

The lifecycle workflow then failed during uninstall on all three distributions:
`rm: cannot remove '/home/nodecore/.node-core': Device or resource busy`.
The workflow had mounted the data directory itself as a Docker bind mount at
`/home/nodecore/.node-core`. A process inside the container cannot remove the
mount point, so this failure was caused by CI mount layout rather than the
application's menu or updater.

Correction:
- Mount the temporary host directory at `/home/nodecore` instead.
- Keep `NODE_CORE_DATA_DIR=/home/nodecore/.node-core` as a normal child
  directory. The product can now remove that child during uninstall without
  attempting to remove a mounted filesystem root.
- Product installation, tests, update and uninstall remain executed as UID
  1001; no root or sudo is used for product operations.

Corrective commit:
- `5022448a6808151bfbeb49b4ab9fc69e82ef03fe` — mount the parent home directory
  so the product data directory is removable by the non-root uninstaller.

Verification status:
- The correction is committed. The workflow run triggered by this commit must
  complete on Ubuntu 24.04, Debian 13 and Fedora 44 before the lifecycle is
  considered passed. A committed correction is not itself a passing test.
