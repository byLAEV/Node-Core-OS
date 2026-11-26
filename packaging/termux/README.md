# Termux packaging adapter

Termux runs on Android/Bionic and uses its own prefix and package ecosystem. Do not install the Debian/glibc package from `packaging/debian` in Termux.

This directory is reserved for a Termux-native package recipe and device test suite. The adapter must use `$PREFIX`, avoid systemd assumptions, and be built/tested inside Termux AArch64. A generated generic Debian archive is not sufficient evidence of Termux compatibility.

Until the native recipe and on-device tests are merged, Termux support is marked **in progress**, not released.
