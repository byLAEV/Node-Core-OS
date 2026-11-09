# LinDesk Lobby adapter

Targets LinDesk running Debian GNU/Linux ARM64 as an unprivileged Android user.

## Install only the Lobby

    curl -fsSL https://raw.githubusercontent.com/byLAEV/Node-Core-OS/feature/lindesk-local-lobby/compatibility/android/lindesk/bootstrap-lobby.sh -o "$HOME/bootstrap-lobby.sh"
    bash "$HOME/bootstrap-lobby.sh"

The bootstrap resolves the branch to a Git commit SHA, downloads that commit archive, validates archive paths and invokes the LinDesk installer.

No root, sudo, apt installation, or system Python modification is required. A virtual environment is kept at ~/.node-core/runtime/lobby-venv.

## Launch

    "$HOME/.local/bin/node-core-lobby"

The Lobby binds to loopback port 8765. This adapter installs and launches the Lobby only; it does not install Node Core OS.

End-to-end compatibility of all preparation and Node Core OS installation actions under Android/PRoot remains to be tested separately.
