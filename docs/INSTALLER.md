# Node Core OS — Installer Specification

## Objective

The installer converts a supported GNU/Linux terminal environment into a usable Node Core OS installation.

The installation boundary is:

```
GNU/Linux terminal
      ↓
Node Core installer
      ↓
dependencies
      ↓
Node Core filesystem
      ↓
Python runtime
      ↓
Kubo
      ↓
Node Core launcher
      ↓
verification
```

## Official platform

Only GNU/Linux is accepted.

The installer must stop before making changes when:

```
uname -s != Linux
```

There is no Android, Termux, Windows, macOS, GUI, or web installer path.

## Installation phases

1. Platform check
2. Dependency check (no host package installation)
3. Prepare user-owned filesystem
4. Install/copy Node Core application
5. Install Kubo and verify checksum
6. Initialize Kubo repository
7. Persist Node Core configuration
8. Prepare launcher
9. Verify Kubo
10. Verify Node Core
11. Run smoke tests
12. Print first-boot instructions

## Installation layout

```
~/.node-core/
├── app/
├── bin/
│   ├── node-core
│   └── ipfs
├── storage/
├── ipfs/
├── logs/
├── runtime/
├── services/
└── config.json
```

The installation is user-owned and therefore does not require a system-wide package manager. Installer, updater, and uninstaller explicitly refuse to run as UID 0 (root). The configured data directory must resolve to a directory inside the current user's HOME; an existing target must be a real directory owned by that user. Run all commands as the normal account, without `sudo`.

## Node Core launcher

The installer creates:

```
~/.node-core/bin/node-core
```

The launcher invokes the installed application with the detected Python 3 interpreter.

The installer does not modify the user's shell startup files automatically. This avoids silently changing shell configuration. It prints an optional PATH command at the end.

## Python

The installer requires Python 3.10 or newer.

The current repository uses only the standard library.

The installer verifies:

- Python executable exists
- Python major/minor version is supported
- Python can compile the Node Core sources


## Evidence and My Life / Node Blog

The installer copies the complete `node_core` application package into `~/.node-core/app/node_core`; it must include `evidence.py` and `my_life.py`. Installation verification checks that both modules exist and compiles the installed Python sources before declaring the application verified.

The Node Core menu exposes **Add Evidence** and **My Life / Node Blog**. Evidence creation stores a local text record and adds it to Kubo/IPFS with pinning. My Life entries are stored in local storage under `storage/my-life/entries/`, with a JSON index at `storage/my-life/index.json`.

My Life entries are **local-only by default**. The user must explicitly choose to add an entry to IPFS and pin it. If IPFS addition fails, the entry remains saved locally and the interface reports the failure. Installing or updating these modules must not delete the user storage directory, the Kubo repository, or the existing configuration.

### My Life entry navigation and publication

The terminal interface displays at most 10 entries per page. Page-local numbers select one entry from the currently displayed page; they are not publication actions. The user opens the selected entry's detail menu before choosing **Publish this entry to IPFS**, then explicitly answers whether to pin the content on this node (`Y` by default, `n` to skip pinning). The operation receives the stable entry ID and updates only the selected record in `my-life/index.json`.

The browser supports next/previous page navigation and search by title, content, or entry ID. The entry's local Markdown file is preserved after successful publication and when publication fails. An IPFS CID is recorded only after Kubo successfully adds the content. The selected pin preference is passed to Kubo; if an existing CID is selected for pinning, Node Core pins that CID instead of re-adding the file. The interface must never interpret a generic menu option as a request to publish every entry.

The updater installs this behavior by replacing the application code from the selected repository commit. It does not replace `storage/my-life/`, the existing Kubo binary, the Kubo repository, or the user configuration. No storage migration is required for existing index records because the entry schema is unchanged.

## Kubo

The Kubo installer performs:

```
detect architecture
      ↓
select pinned release
      ↓
download archive
      ↓
download SHA-512 file
      ↓
verify archive
      ↓
extract
      ↓
install ~/.node-core/bin/ipfs
      ↓
ipfs version
      ↓
ipfs init
      ↓
health check
```

The initial implementation pins Kubo v0.43.1.

Supported installer architectures:

- Linux AMD64
- Linux ARM64

Other Linux architectures fail explicitly until their archive mapping is implemented and tested.

## Kubo configuration

Node Core uses:

```
IPFS_PATH=~/.node-core/ipfs
API=http://127.0.0.1:5001
Gateway=http://127.0.0.1:8080
```

Kubo remains responsible for its own repository, daemon, API, gateway, peer identity, content addressing and pinning.

Node Core only provides the abstraction used by the Node Core menus and runtime.

## Service lifecycle

The installer must not make systemd a universal prerequisite.

The first installer baseline supports a user-owned/manual Kubo lifecycle through Node Core's existing Kubo manager. A future service adapter can use `systemd --user` or another Linux supervisor when available.

The abstraction is:

```
Node Core
   ↓
Service Manager
   ↓
Linux service supervisor (optional)
   ↓
Kubo
```

## Verification contract

A successful installation must verify:

```
GNU/Linux       ✓
Bash            ✓
Python          ✓
Node Core files ✓
Kubo binary     ✓
Kubo repository ✓
Kubo API        ✓
Launcher        ✓
Python compile  ✓
```

If any mandatory verification fails, installation exits non-zero.

## Uninstallation

Uninstallation must stop a Node Core-managed Kubo process when possible and remove only the Node Core installation owned by the user.

The uninstall command must clearly distinguish:

- application/launcher files
- Node Core data
- Kubo repository/content

The first implementation should require explicit confirmation before deleting `~/.node-core`.

## Design constraints

The installer intentionally avoids:

- root as a universal prerequisite
- sudo as a universal prerequisite
- systemd as a universal prerequisite
- fixed system paths
- graphical installers
- platform-specific branches for Termux/Android
- unversioned Kubo downloads


## Host package resolution

The installer never installs host packages. It checks for the terminal utilities it actually uses and stops with a clear dependency message when one is missing. This avoids root, sudo, system package managers, and fixed system paths. CI tests explicitly exercise the root-rejection and HOME-boundary guards.

## Third-party installation boundary

The installer installs Kubo as external infrastructure. Python third-party packages are intentionally not required by the current runtime.

The resulting dependency model is:

```
GNU/Linux
├── Bash
├── Python 3.10+
├── tar
├── coreutils / sha512sum
├── awk
├── curl or wget
└── Kubo
```

The user may install missing host utilities through the package mechanism available in their Linux environment before rerunning the installer.

## Persistent Kubo lifecycle

If a usable `systemd --user` environment is detected, the installer creates and enables a user service for Kubo. Otherwise Kubo remains in the Node Core-managed manual lifecycle. This keeps systemd optional while still providing persistent service integration where the Linux environment supports it.
