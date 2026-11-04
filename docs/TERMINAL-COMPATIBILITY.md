# Node Core OS Terminal Compatibility Layer (NCTCL)

**Contract:** \`NCTCL-1\`  
**Machine-readable manifest:** [\`compatibility/manifest.json\`](../compatibility/manifest.json)  
**JSON Schema:** [\`schemas/compatibility-manifest.schema.json\`](../schemas/compatibility-manifest.schema.json)  
**CLI:** \`python3 -m node_core.compatibility\`

## Objective

NCTCL makes compatibility a repository-owned, executable contract. One Node Core OS
product and one installer detect the Linux terminal environment, compare actual
capabilities against versioned manifests, select the applicable platform profile and
report blockers before application installation or update changes are made.

It does not maintain a separate Node Core product for each terminal emulator or shell.
GNOME Terminal, Konsole, Xfce Terminal, Alacritty, kitty, Foot, xterm-compatible
terminals and terminal multiplexers are not an allowlist. Node Core checks POSIX
terminal capabilities such as TTY availability, TERM and ANSI support, then uses a
generic text fallback when required.

## Supported profiles in this contract

| Profile | Architectures | Distribution/environment policy |
|---|---|---|
| GNU/Linux | x86_64, aarch64 | Capability-based; an unknown distribution is not rejected solely because its ID is not listed |
| Native Termux | aarch64 | Requires native Termux markers, pkg and Android-native packages |

Other operating systems and architectures fail closed until a new profile is declared
and tested. Matching a profile is a compatibility decision, not proof of a successful
installation on every distro, terminal emulator or kernel.

The detector records distribution ID/version, architecture, libc family, Python
version, installer shell, terminal indicators, TTY/ANSI capability, command availability,
package-manager presence, Kubo CLI and optional systemd-user availability. It does not
source \`/etc/os-release\`, execute shell startup files or invoke host package managers.

## Decision states

- \`ready\`: declared platform and required capabilities are present.
- \`requires_preparation\`: platform profile is eligible, but Python or one or more host
  commands must be prepared before installation/update.
- \`unsupported\`: operating system, environment family or architecture is outside
  declared profiles. The installer/update must stop.

A no-TTY environment or \`TERM=dumb\` is reported as a limitation, not misidentified as
an unsupported operating system. Interactive menus require a real interactive TTY;
plain text fallback is required when ANSI support is unavailable.

## Installer integration

The canonical installer runs NCTCL after host dependency preparation and before
creating or replacing the Node Core application tree. Native Termux may prepare its
user-space packages through \`pkg\`; GNU/Linux package managers are never invoked.
The updater runs the same preflight before recovery reconciliation or application
mutation when the compatibility contract is present.

The preflight is read-only. It does not install packages, write configuration, alter
storage, initialize identity, start Kubo or change system services. A failed preflight
must produce a non-zero result and a report with missing requirements and recommended
actions.

## Service and runtime adapters

- \`systemd --user\` is optional; use the manual Node Core service lifecycle when the
  user manager is unavailable.
- GNU/Linux uses the declared Linux Kubo binary path selected by the installer.
- Termux uses Android-native Python cryptography and Kubo packages.
- Terminal presentation is capability-driven; color and cursor controls are optional.

## Diagnostics

From a repository checkout:

\`\`\`bash
PYTHONPATH="$PWD" python3 -m node_core.compatibility --mode diagnose
PYTHONPATH="$PWD" python3 -m node_core.compatibility --mode diagnose --json
python3 -m unittest tests.test_compatibility -v
bash installer/tests/compatibility.sh
\`\`\`

From an installed node:

\`\`\`bash
"$HOME/.node-core/bin/node-core-compatibility" --mode diagnose
\`\`\`

A profile match is not an E2E pass. A real compatibility claim additionally requires
successful CI or physical-device installation evidence for that exact distribution
and architecture.
