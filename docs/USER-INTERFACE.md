# User-only text interface

- Plain terminal text, no graphical toolkit, images, animation, web UI, or touch events.
- Numeric menu choices entered through stdin; invalid input is rejected and the menu remains active.
- Small Python standard-library CLI; no runtime third-party Python dependencies.
- Default application data: `~/.local/share/node-core-os`; override with `NODE_CORE_OS_HOME`.
- Installation code and launcher: `~/.local/lib/node-core-os` and `~/.local/bin/node-core-os`.
- Installer must run as the normal user and must not request elevation.
- Shell and CLI are designed for low memory, but memory consumption must be measured on supported devices before publishing a quantitative claim.
