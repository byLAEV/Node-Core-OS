# User-only installation (no root)

The recommended installer is:

```sh
./packaging/user/install.sh
```

It installs the command and application code only into the invoking user's `~/.local/bin` and `~/.local/lib/node-core-os`, with data under `~/.local/share/node-core-os`. It does not call `sudo`, `dpkg`, a system service manager, or write to system directories.

Runtime requirements: Python 3 (standard library only). The text menu accepts typed numeric choices; it has no graphics, images, mouse or touch interaction.

To remove the application, delete the installed executable and code directories manually. Keep the user data directory unless you intentionally want to delete your own data.

The existing Debian .deb remains a distribution artifact for system package managers and is not a user-only installer. Do not install that .deb with dpkg when the requirement is a no-root per-user installation.
