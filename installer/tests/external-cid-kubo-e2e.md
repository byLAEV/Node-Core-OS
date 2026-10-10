# External CID Library live Kubo E2E coverage

The installer E2E workflow exercises `ExternalCIDLibrary` against the Kubo daemon installed and started by the installer, running as a non-root user.

The workflow creates a small local fixture and adds it to Kubo without pinning it, then verifies:
- Local reference creation, reload, search, and metadata update.
- Retrieval through the Kubo RPC API and byte-for-byte content equality.
- Pin creation and local pin-status detection.
- Removing a library reference does not remove the Kubo pin.
- Explicit unpinning updates the reported local pin status.

The fixture is created by the workflow and does not require a public gateway or third-party content provider. It validates the real Kubo RPC integration without making CI dependent on external IPFS peers. It does not claim to validate retrieval from a remote peer or global availability across the IPFS network.
