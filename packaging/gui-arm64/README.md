# Node Core OS GUI 1.5.6

The GUI is a local-only responsive browser dashboard implemented with the Python 3.10+ standard library. It binds to 127.0.0.1 only and opens the system browser. It does not replace the canonical Node Core engine installer.

## Target compatibility

- GNU/Linux x86_64 and aarch64 with Python 3.10+ and a browser.
- Debian-family systems: install the architecture-independent `all` DEB.
- Other Linux distributions: use the portable archive.
- Termux on Android aarch64: install Python with `pkg install python`, extract the portable archive, and run `python app.py`. Install the Node Core engine and Kubo using the canonical Termux-aware installer.

The GUI package is architecture-independent; the Node Core engine has its own platform compatibility contract. Do not infer that every distribution has passed validation merely because Python runs.

## Portable launch

```sh
python3 app.py
```

Stop the local dashboard with Ctrl+C in the launching terminal.
