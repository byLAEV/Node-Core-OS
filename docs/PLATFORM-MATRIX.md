# Platform compatibility matrix

| Target | CPU | Runtime / libc | Packaging | Status |
|---|---|---|---|---|
| Debian/Ubuntu | ARM64 | Linux / glibc | Native .deb | Build target; device validation pending |
| Termux | AArch64 | Android / Bionic | Termux-native package | Adapter design; native build and device tests pending |
| Lindesk | To verify | To verify | To verify | Unknown until distribution details are confirmed |

A Debian `arm64` package is not interchangeable with a Termux package merely because both use the Debian archive format internally. Termux uses Android/Bionic, its own prefix, and its own package repository conventions.

Do not advertise Lindesk compatibility until its base distribution, architecture, libc, and package manager are established.
