# GNU/Linux installation boundary

The host installer is responsible for platform detection, dependency verification, user-level installation, data-preserving updates and safe uninstall. It must reject Android/Termux and unsupported operating systems before writing files or changing services.

The currently tested entry point remains `installer/install.sh` until the new `installer/linux/` implementation is proven equivalent. This directory is a migration destination, not yet the canonical executable installer.
