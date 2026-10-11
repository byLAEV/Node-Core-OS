# Changelog

All notable changes to Node Core OS are documented here.

## [Unreleased]

### Added
- Document good-faith identity UX, privacy-by-default, declared-versus-verified status, and layered future security controls in `docs/IDENTITY-DESIGN-PRINCIPLES.md`.
- Add a local text-only identity profile under the Node Core BIOS, with explicit association to an available Kubo Peer ID.
- Show all locally saved identity fields in the main menu, including the document number, logical identity ID, and node association, while clearly marking network-consensus verification as not verified.
- Add optional date of birth, height in centimeters, and self-described gender fields, with input validation and explicit declared-data semantics.
- Release the identity-profile and updater integration as Node Core OS 1.2.2; require installer verification to find the identity-profile module and test that updates deploy it without replacing persistent data.
- Display the first-entry and last-updated timestamps for identity data in ISO-8601 UTC format.
- Add tests for local persistence, stable logical identity, node association, and private file permissions.

### Security and scope
- Profile data remains local and is not automatically sent to IPFS. Full-value display in the single-user local menu does not imply network publication or external disclosure.
- Entered identity data is marked declared, not verified. Issuer corroboration, holder verification, personhood checks, and duplicate prevention are not implemented by this profile.

## [1.2.1] - 2026-10-10

This is a maintenance and reliability release focused on safer user-level updates and recovery.

### Added
- Guard against starting another update while recovery artifacts from a failed rollback remain.
- Regression coverage for failed rollback and subsequent update attempts.
- Explicit preservation checks for the installed application, commit marker, local storage, Kubo/IPFS repository, executable, and configuration during updater failure scenarios.

### Changed
- Validate the remote Git commit identifier before attempting to install an update.
- Back up and restore the installed commit marker together with the application during rollback.
- Retain recovery files when rollback fails and report the recovery directory instead of claiming recovery succeeded.
- Refuse another update until retained recovery artifacts have been inspected.

### Validation
- GNU/Linux Terminal CI: passed for the current main commit before release preparation.
- Installer E2E on Ubuntu 24.04 x86_64: passed for the current main commit before release preparation, including user-systemd and no-user-systemd scenarios.
- The tests run as an unprivileged user and do not require root or sudo.
- Real-device Termux validation is not claimed by these Linux CI results.

### Scope and limitations
- This release does not replace the local storage directory, Kubo executable, or IPFS repository during an application update.
- A failed rollback retains recovery files for manual recovery. Do not delete them until the installed application and commit marker have been verified.
- Identity, reputation, distributed consensus, and other roadmap capabilities must not be interpreted as fully operational solely because they are documented.

