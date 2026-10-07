# Node Core OS Security

## V1 backup security model

Kubo private cryptographic material is sensitive data. The intended pipeline is Kubo -> temporary material -> age encryption -> encrypted backup -> destination.

Private key material must never be uploaded to IPFS or Pinata in plaintext.

Pinata authentication is separate from Node identity. The user authenticates to Pinata's web console and creates an API credential; Node Core OS uses that credential for API requests and does not perform Google/GitHub login itself.

Pinata credentials must not be stored in config.json, Git history, or a Node identity backup.

Destructive restore and key rotation are deferred until the encrypted backup round-trip is proven.
