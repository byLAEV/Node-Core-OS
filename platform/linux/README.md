# Linux platform adapter

This directory is the canonical home for GNU/Linux-specific adapters: distribution/package metadata, system integration, service-manager integration and platform capability checks.

Migration rule: existing tested implementations remain in their current paths until each relocation updates imports, installer references, tests and CI together. Do not duplicate executable adapters here merely to imply migration completion.

Runtime target: GNU/Linux only. Android/Termux is not a runtime profile.
