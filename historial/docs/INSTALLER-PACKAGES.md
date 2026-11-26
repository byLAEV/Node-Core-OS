# Node Core OS byLAEV — single installer and updater contract

Every release publishes exactly two downloadable archives:

1. `node-core-os-install-VERSION.tar.gz` — the only fresh installer.
2. `node-core-os-update-VERSION.tar.gz` — the only self-contained updater.

No distribution/architecture variants, duplicate BIOS packages or separate checksum files are published. SHA-256 and SHA-512 digests are embedded in the GitHub Release notes.

## One installer

Extract the installer archive and run as the ordinary user:

```bash
bash installer/install.sh
```

This entry point detects GNU/Linux or native Termux and selects compatible dependencies internally. The legacy `installer/termux-install.sh` is a compatibility alias, not a separate download.

## One updater

Extract the updater archive and run as the ordinary user:

```bash
bash update.sh
```

It contains the protected updater and exact matching source snapshot; application source download is not required.

## Platform boundaries

The same two archives are used across supported environments. Environment-specific dependency selection occurs inside the installer. The current bundled GNU/Linux Kubo and Python wheelhouse target Ubuntu 24.04 x86_64. Other supported GNU/Linux architectures may obtain matching Kubo dependencies from official upstream sources. Termux uses native Android ARM64 packages and must not install GNU/Linux wheels.

CI does not replace a physical Termux/Android smoke test. Do not claim every distribution, architecture, shell or Android device has been individually tested.

## Publication ownership

Only `.github/workflows/bios-release-packages.yml` may package and publish a release. `.github/workflows/package-installers.yml` is validation-only and does not respond to version tags, upload artifacts or publish releases.

The publishing workflow uploads exactly the two `.tar.gz` archives and verifies the Release contains exactly two assets. Checksums are in the Release notes, not separate downloadable files.

HashPaper and P2P Contracts remain excluded from installable packages while suspended.
