# Node Core OS Installer and Updater Evolution

## Purpose

This document describes the current safety contract and the remaining work for the Node Core OS installer, updater, and repair flow. All installation and update operations must run as the normal user, without root, sudo, or global system changes.

A capability is considered implemented only when code and automated tests support it.

## Safety rules

1. Reject UID 0 before modifying installation files.
2. Keep `NODE_CORE_DATA_DIR` inside the current user's HOME and validate ownership and path safety.
3. Do not replace a functioning Kubo binary during a normal application update.
4. Never delete or rebuild `storage/` or `ipfs/` during an application update.
5. Preserve `config.json` except for an explicitly required, validated compatibility migration.
6. Download and validate release code before marking it as installed.
7. Back up the current application and restore it when an update fails.
8. Treat network errors as failures; never report an update as successful when the remote commit could not be checked.
9. Update the installed commit marker only after compilation and application checks pass.
10. Test clean installation, existing-install updates, rollback, and data preservation in CI.

## Current implementation

- The clean installer now refuses to overwrite an existing application directory. Existing users must use `~/.node-core/bin/node-core-update`.
- The clean installer creates the Node Core OS launcher, updater launcher, and user-level HashPaper launcher.
- The updater downloads source for the requested commit and retains a backup of the previous application and commit marker for rollback.
- The updater validates that the new source includes the HashPaper entry point, CLI module, and tests.
- The updater compiles Node Core OS and HashPaper Python code and runs the HashPaper unit test suite before recording the new commit as installed.
- A successful application update does not replace Kubo, its repository, local storage, HashPaper documents, OTS proofs, generated packages, publication records, or configuration.
- The update-preservation test exercises successful update, failure rollback, corrupt archive handling, download failure handling, persistent data preservation, and refusal to overwrite an existing install.
- The installer verifier checks that HashPaper's entry point and CLI exist and compile, and that its launcher is present.
- `installer/lib/apply.sh` provides a separate transactional deployment primitive with its own tests. It is not yet the shared implementation used by both the clean installer and network updater.

## Persistent data layout

Application code is installed under:

```text
~/.node-core/app/
```

Persistent user data is kept outside that replaceable code directory:

```text
~/.node-core/config.json
~/.node-core/storage/
~/.node-core/ipfs/
~/.node-core/hashpaper/documents/
~/.node-core/hashpaper/proofs/
~/.node-core/hashpaper/packages/
~/.node-core/hashpaper/records/
```

The updater must not include these paths in its application replacement or rollback operations.

## HashPaper integration

HashPaper is included in the main Node Core OS application source. A normal update to the latest main-branch commit delivers HashPaper changes alongside the core application. The updater validates the HashPaper files, compiles them, runs `python3 -m unittest discover -s applications/hashpaper/tests -p 'test_*.py' -v` from the application root, and rolls back if validation fails.

The user-level command is:

```bash
~/.node-core/bin/hashpaper
```

OpenTimestamps proof status is not inferred from file existence. A pending proof remains pending until the official client verifies an attestation. HashPaper encryption is **NOT IMPLEMENTED**; generated evidence packages contain the complete original text and included identity fields in cleartext.

## Remaining work

- Integrate the shared transactional deployment primitive into both clean installation and network update flows.
- Complete atomic activation and recovery for failures that occur during commit-marker writes and launcher creation.
- Add an explicit versioned component inventory and migration plan.
- Extend clean-install idempotency and repair workflows without overwriting user configuration.
- Continue running the live OpenTimestamps and Kubo/IPFS workflow and preserve its evidence artifacts. A passing CI run with `WAITING_FOR_BITCOIN` does not establish Bitcoin attestation verification.
- Do not declare Termux/Android officially supported unless the project adds a documented support contract and dedicated tests.

## Acceptance criteria

- Clean install and existing-install update run as a non-root user.
- A clean installer invocation cannot erase an existing application.
- A successful update includes HashPaper and its verified test suite.
- A failed update restores the previous application and commit marker.
- Kubo, the IPFS repository, local storage, HashPaper data, and user configuration survive both successful and failed application updates.
- Missing or corrupt release content is rejected.
- CI results are checked before a pull request is merged.
