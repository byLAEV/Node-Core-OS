# User-only and low-memory design

- The installer rejects UID 0 and never invokes sudo, su, apt install, systemctl, or writes to /usr.
- The user installer extracts the .deb and installs under ~/.local/lib and ~/.local/bin.
- Persistent data remains under ~/.local/share/node-core-os.
- Interface: plain terminal text and numeric stdin choices. No images, GUI, touch event handlers, curses, animation, or background polling.
- Runtime uses Python standard library only and launches on demand; no resident daemon.
- The .deb is a package archive. Use install-user.sh for unprivileged per-user installation.
- Termux needs target-device validation for Python and dpkg-deb; compatibility remains unverified until tested.
