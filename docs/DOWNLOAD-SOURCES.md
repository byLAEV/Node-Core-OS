# HashPaper for Node Core OS — official download sources and fallbacks

This document records the trusted upstream sources used by the user-only installers. The installers must not use `sudo`, run as UID 0, or write to system directories.

## Node Core OS application updates

The updater resolves a branch commit using these official GitHub API routes, in order:

1. `https://api.github.com/repos/byLAEV/Node-Core-OS/commits?sha=<encoded-branch>&per_page=1`
2. `https://api.github.com/repos/byLAEV/Node-Core-OS/commits/<encoded-branch>`

It validates the returned 40-character commit SHA before saving metadata. Source archives are then attempted in order:

1. `https://github.com/byLAEV/Node-Core-OS/archive/<commit>.tar.gz`
2. `https://codeload.github.com/byLAEV/Node-Core-OS/tar.gz/<commit>`

The updater validates the downloaded archive before changing the installed application. A network failure or invalid archive must abort without replacing the installed application.

## Kubo / IPFS

For GNU/Linux, the installer downloads the configured, pinned Kubo version from the official sources in this order:

1. GitHub Releases: `https://github.com/ipfs/kubo/releases/download/v<VERSION>/`
2. IPFS Distributions: `https://dist.ipfs.tech/kubo/v<VERSION>/`

Both the archive and its SHA-512 checksum are fetched from the same source. The checksum must pass before extraction or installation. If a source fails, the installer deletes partial files before trying the next source. It must not mix an archive from one source with a checksum from another.

On Termux, Node Core OS preserves and uses an existing Android-compatible `$PREFIX/bin/ipfs`; it must not replace that executable with a GNU/Linux binary.

Official upstream: https://github.com/ipfs/kubo  
Official distribution site: https://dist.ipfs.tech/

## OpenTimestamps client and Python library

The installer uses the official client release `opentimestamps-client-v0.7.2` and keeps it in the private virtual environment under `~/.node-core/runtime/opentimestamps-venv`.

Sources, in order:

1. PyPI package pinned to `opentimestamps-client==0.7.2`: `https://pypi.org/project/opentimestamps-client/0.7.2/`
2. Official GitHub release-tag archive: `https://github.com/opentimestamps/opentimestamps-client/archive/refs/tags/opentimestamps-client-v0.7.2.tar.gz`
3. Official GitHub codeload archive for the same tag: `https://codeload.github.com/opentimestamps/opentimestamps-client/tar.gz/refs/tags/opentimestamps-client-v0.7.2`

After installation, the installer checks both `ots --help` and `import opentimestamps`. All pip operations target the private venv; system Python is not modified. Source archive fallbacks remain pinned to the same upstream release tag.

Official upstream: https://github.com/opentimestamps/opentimestamps-client  
Official Python package: https://pypi.org/project/opentimestamps-client/

## Optional OpenTimestamps calendar server

The optional server setup uses the official repository:

- https://github.com/opentimestamps/opentimestamps-server

The optional installer attempts the official Git clone first, then official GitHub archive and codeload URLs if Git is unavailable or cloning fails. An archive-based checkout is marked with the official repository URL so a later run can verify it without overwriting it. This component is not required to use HashPaper with public calendars. Preparing its source/dependencies does not start a server or make a calendar operational. Running a calendar requires separate Bitcoin Core/wallet configuration, secrets, stable URI, monitoring, and network security.

## Download safety requirements

- Try sources sequentially; do not write multiple downloads to the same destination concurrently.
- Remove partial files between source attempts.
- Retry transient connection failures, but do not impose a short total-transfer timeout on large Kubo archives.
- Verify Kubo SHA-512 before extraction.
- Validate GitHub commit metadata and source archive format before updating.
- Never silently fall back to an untrusted mirror or a third-party package repository.
- Keep all source, cache, virtual environment, and installed application paths under the current user's home directory.
- If all official sources fail, stop with an actionable error and preserve the existing application and user data.
