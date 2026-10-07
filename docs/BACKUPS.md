# Node Core OS V1 Backups

V1 destinations:

- Local backup directory.
- External/custom file path, including mounted USB storage.
- Pinata remote storage for the encrypted backup.

The backup flow is Kubo -> temporary material -> age encryption -> encrypted .ncb -> destination.

The manifest contains non-secret metadata such as creation time, Kubo version, PeerID, and key names. It must never contain private keys or provider credentials.

Automatic destructive restore is not part of the first V1 implementation.
