# Node Core OS 1.5.6 — LinDesk ARM64 user-mode DEB

This package carries the exact historical source commit selected for the 1.5.6 build. It does not run the core installer from dpkg maintainer scripts.

## Install the DEB without root (recommended for LinDesk user-mode)

```sh
mkdir -p "$HOME/Downloads/node-core-os-deb"
cd "$HOME/Downloads/node-core-os-deb"
# Download the DEB artifact from the project's validated GitHub Actions run.
dpkg-deb --extract node-core-os_1.5.6-1_arm64.deb "$HOME/.local/lib/node-core-os-deb"
bash "$HOME/.local/lib/node-core-os-deb/opt/node-core-os-1.5.6/install-user.sh"
```

The package manager is not invoked by the user installer. The Node Core runtime and data are installed under `$HOME/.node-core`. Run as a normal user, never with sudo.

## Conventional Debian installation

`sudo apt install ./node-core-os_1.5.6-1_arm64.deb` installs only the immutable application source and launcher into /opt and /usr/bin. It does not execute the Node Core installer. Then run `node-core-os-install-user` from the normal user session.

## Resource and compatibility policy

The user installer reports architecture, memory, swap, cgroup memory limits, virtualization/container hints, available home storage and required commands before invoking the canonical installer. Resource measurements are diagnostic and do not invent a minimum RAM requirement. The canonical compatibility preflight remains authoritative.

The package never runs the core as root, never installs host dependencies using apt, never modifies system services, and never deletes existing user data. Kubo remains a separately managed executable and repository under the user's Node Core data directory.
