# NODE CORE OS Lobby for Termux

Standalone, read-only first implementation of the local administration Lobby. It uses Python standard library only and binds exclusively to 127.0.0.1:8765 over HTTP.

Install from Termux by running `bash install.sh` from this directory. The installer writes only `~/.node-core/lobby/` and the `$PREFIX/bin/node-lobby` launcher. It does not install, update, repair, or overwrite the Node Core OS runtime.

Run with `node-lobby`. Open http://127.0.0.1:8765/. Diagnostics are read-only. Install/update/repair controls are deliberately not connected.
